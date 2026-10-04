#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EC-CUBE 商品価格一括改定スクリプト
CSVファイル（EC-CUBE商品CSV形式）を入力として、既存商品の価格改定用SQLを生成または直接適用します。
"""

import os
import sys
import csv
import argparse
import unicodedata
import subprocess
from datetime import datetime

def clean_price(val):
    """金額文字列のクレンジング（カンマ除去、全角数字変換、空白除去）"""
    if val is None:
        return None
    val = unicodedata.normalize('NFKC', str(val)).strip()
    val = val.replace(',', '').replace('¥', '').replace('\\', '').strip()
    if not val:
        return None
    try:
        # 小数点または整数
        f_val = float(val)
        # 整数値として表せる場合は整数表示
        if f_val.is_integer():
            return int(f_val)
        return f_val
    except ValueError:
        return None

def detect_encoding(file_path):
    """ファイルの文字コードを簡易判定"""
    for enc in ['utf-8-sig', 'utf-8', 'cp932', 'euc-jp']:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'

def parse_csv(csv_path):
    """CSVを読み込み、価格改定用レコードを抽出・検証"""
    encoding = detect_encoding(csv_path)
    records = []
    errors = []
    
    with open(csv_path, 'r', encoding=encoding, errors='replace') as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip() for c in reader.fieldnames or []]
        
        # 必須カラムチェック
        required_cols = ['商品ID', '販売価格']
        for col in required_cols:
            if col not in fieldnames:
                raise ValueError(f"CSVに必要なカラム '{col}' が見つかりません。ヘッダー一覧: {fieldnames}")
        
        has_class1 = '規格分類1(ID)' in fieldnames
        has_class2 = '規格分類2(ID)' in fieldnames
        has_price01 = '通常価格' in fieldnames
        
        for row_num, row in enumerate(reader, start=2):
            raw_pid = row.get('商品ID', '').strip()
            raw_p02 = row.get('販売価格', '')
            raw_p01 = row.get('通常価格', '') if has_price01 else None
            raw_c1 = row.get('規格分類1(ID)', '').strip() if has_class1 else ''
            raw_c2 = row.get('規格分類2(ID)', '').strip() if has_class2 else ''
            product_name = row.get('商品名', '').strip()
            product_code = row.get('商品コード', '').strip()
            
            # 商品IDの検証
            if not raw_pid or not raw_pid.isdigit():
                errors.append((row_num, f"不正な商品ID: '{raw_pid}'"))
                continue
            product_id = int(raw_pid)
            
            # 販売価格のクレンジング・検証
            price02 = clean_price(raw_p02)
            if price02 is None or price02 < 0:
                errors.append((row_num, f"商品ID={product_id}: 不正な販売価格 '{raw_p02}'"))
                continue
            
            # 通常価格のクレンジング
            price01 = clean_price(raw_p01) if raw_p01 else None
            
            # 規格IDのクレンジング
            c1_id = int(raw_c1) if raw_c1 and raw_c1.isdigit() else None
            c2_id = int(raw_c2) if raw_c2 and raw_c2.isdigit() else None
            
            records.append({
                'row_num': row_num,
                'product_id': product_id,
                'product_name': product_name,
                'product_code': product_code,
                'class_category_id1': c1_id,
                'class_category_id2': c2_id,
                'price01': price01,
                'price02': price02,
                'raw_p02_has_comma': ',' in str(raw_p02)
            })
            
    return records, errors, encoding

def generate_sql(records, output_sql_path):
    """UPDATE SQLスクリプトを生成"""
    product_ids = sorted(list(set(r['product_id'] for r in records)))
    
    lines = []
    lines.append("-- ========================================================")
    lines.append(f"-- EC-CUBE 価格一括改定スクリプト")
    lines.append(f"-- 作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 対象件数: {len(records)} 規格 (商品数: {len(product_ids)})")
    lines.append("-- ========================================================")
    lines.append("")
    lines.append("SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;")
    lines.append("SET SQL_SAFE_UPDATES = 0;")
    lines.append("START TRANSACTION;")
    lines.append("")
    lines.append("-- 1. dtb_product_class (規格別価格・更新日時) のUPDATE")
    
    for r in records:
        pid = r['product_id']
        c1 = r['class_category_id1']
        c2 = r['class_category_id2']
        p02 = r['price02']
        p01 = r['price01']
        
        # WHERE句の構築 (規格あり/なし、visible=1)
        where_conds = [f"product_id = {pid}"]
        if c1 is not None:
            where_conds.append(f"class_category_id1 = {c1}")
        else:
            where_conds.append("class_category_id1 IS NULL")
            
        if c2 is not None:
            where_conds.append(f"class_category_id2 = {c2}")
        else:
            where_conds.append("class_category_id2 IS NULL")
            
        where_conds.append("visible = 1")
        where_clause = " AND ".join(where_conds)
        
        # SET句の構築
        p01_val = f"{p01:.2f}" if p01 is not None else "NULL"
        p02_val = f"{p02:.2f}"
        
        comment = ""
        if r['product_code']:
            comment = f" -- {r['product_code']}"
            if r['product_name']:
                comment += f" ({r['product_name'][:15]})"
                
        lines.append(
            f"UPDATE dtb_product_class SET price01 = {p01_val}, price02 = {p02_val}, update_date = NOW() "
            f"WHERE {where_clause};{comment}"
        )
    
    lines.append("")
    lines.append("-- 2. dtb_product (商品基本テーブル) の更新日時 (update_date) を更新")
    # 分割してIN句を安全に更新
    chunk_size = 500
    for i in range(0, len(product_ids), chunk_size):
        chunk = product_ids[i:i + chunk_size]
        ids_str = ", ".join(map(str, chunk))
        lines.append(f"UPDATE dtb_product SET update_date = NOW() WHERE id IN ({ids_str});")
        
    lines.append("")
    lines.append("COMMIT;")
    lines.append("SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;")
    lines.append("")
    
    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="EC-CUBE 商品価格一括改定ツール")
    parser.add_argument("--csv", default="product_newprice.csv", help="入力CSVファイルパス (デフォルト: product_newprice.csv)")
    parser.add_argument("--output-sql", default="update_product_newprice.sql", help="出力SQLファイルパス (デフォルト: update_product_newprice.sql)")
    parser.add_argument("--dry-run", action="store_true", help="SQL生成やDB実行を行わず、CSVの検証のみ実行")
    parser.add_argument("--execute", action="store_true", help="生成したSQLをmysqlコマンド経由でDBに即座に実行")
    parser.add_argument("-H", "--host", default="localhost", help="MySQLホスト名 (デフォルト: localhost)")
    parser.add_argument("-P", "--port", type=int, default=3306, help="MySQLポート番号 (デフォルト: 3306)")
    parser.add_argument("-u", "--user", default="root", help="MySQLユーザー名 (デフォルト: root)")
    parser.add_argument("-p", "--password", default=None, help="MySQLパスワード")
    parser.add_argument("-d", "--dbname", default=None, help="MySQLデータベース名")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv):
        print(f"エラー: CSVファイル '{args.csv}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] CSVファイルを読み込み中: {args.csv}")
    records, errors, encoding = parse_csv(args.csv)
    print(f"    - 文字コード: {encoding}")
    print(f"    - 読込レコード数: {len(records)} 件")
    
    comma_count = sum(1 for r in records if r['raw_p02_has_comma'])
    if comma_count > 0:
        print(f"    - [補正検知] 金額にカンマが含まれていた行: {comma_count} 件 (自動クレンジング済み)")
    
    price01_count = sum(1 for r in records if r['price01'] is not None)
    print(f"    - 通常価格(price01)あり: {price01_count} 件 / NULL: {len(records) - price01_count} 件")
    
    unique_products = len(set(r['product_id'] for r in records))
    print(f"    - 対象商品数(dtb_product): {unique_products} 件")
    
    if errors:
        print(f"\n[!] 警告: スキップされた不正行が {len(errors)} 件あります:")
        for r_num, msg in errors[:10]:
            print(f"    行 {r_num}: {msg}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
            
    if args.dry_run:
        print("\n[+] Dry-run 完了。SQLファイルの生成およびDB更新は行われませんでした。")
        return

    # SQLファイル生成
    print(f"\n[*] SQLファイルを生成中: {args.output_sql}")
    generate_sql(records, args.output_sql)
    print(f"[+] SQLファイルを生成しました: {args.output_sql}")

    # 直接実行モード
    if args.execute:
        if not args.dbname:
            print("エラー: --execute を指定する場合は --dbname (データベース名) を指定してください。", file=sys.stderr)
            sys.exit(1)
            
        print(f"\n[*] データベース '{args.dbname}' に SQL を適用中...")
        cmd = ["mysql", "-h", args.host, "-P", str(args.port), "-u", args.user]
        if args.password:
            cmd.append(f"-p{args.password}")
        cmd.append(args.dbname)
        
        try:
            with open(args.output_sql, 'r', encoding='utf-8') as sql_file:
                res = subprocess.run(cmd, stdin=sql_file, capture_output=True, text=True, check=True)
            print("[+] データベースへの反映が正常に完了しました！")
            print("    ※ 反映後はEC-CUBEのキャッシュクリア (bin/console cache:clear) を推奨します。")
        except subprocess.CalledProcessError as e:
            print(f"[!] データベース実行エラー:\n{e.stderr}", file=sys.stderr)
            sys.exit(e.returncode)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EC-CUBE 商品価格改定 SQL生成スクリプト
指示CSV（EC-CUBE商品CSV形式）を入力とし、安全に本番DBへ適用できる更新用SQLファイルを生成します。
直接DBへ接続・書き込みは行わず、SQLファイルの生成に専念するため安全です。
"""

import os
import sys
import csv
import argparse
import unicodedata
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
        f_val = float(val)
        if f_val.is_integer():
            return int(f_val)
        return f_val
    except ValueError:
        return None

def detect_encoding(file_path):
    """CSVの文字コードを判定 (UTF-8 with BOM, UTF-8, CP932/Shift_JIS)"""
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

def generate_sql(records, output_sql_path, include_backup_table=True):
    """安全なUPDATE SQLスクリプトを生成"""
    product_ids = sorted(list(set(r['product_id'] for r in records)))
    today_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    lines = []
    lines.append("-- ====================================================================")
    lines.append(f"-- EC-CUBE 商品価格一括改定 SQL")
    lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 対象件数: {len(records)} 規格 (親商品数: {len(product_ids)} 件)")
    lines.append("-- ====================================================================")
    lines.append("")
    
    if include_backup_table:
        lines.append("-- --------------------------------------------------------------------")
        lines.append("-- [安全策] 事前バックアップ用テーブル作成クエリ")
        lines.append("-- 実行しておくと、万一元に戻したい場合に一瞬でロールバック可能です。")
        lines.append("-- --------------------------------------------------------------------")
        lines.append(f"CREATE TABLE IF NOT EXISTS `bk_product_class_price_{today_str}` AS")
        lines.append("SELECT `id`, `product_id`, `class_category_id1`, `class_category_id2`, `price01`, `price02`, `update_date`")
        lines.append("FROM `dtb_product_class`;")
        lines.append("")
        
    lines.append("-- --------------------------------------------------------------------")
    lines.append("-- 更新処理本体 (トランザクション開始)")
    lines.append("-- ※ EC-CUBE は DB の日時を UTC として扱うため、update_date は UTC_TIMESTAMP() で格納します。")
    lines.append("-- --------------------------------------------------------------------")
    lines.append("SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;")
    lines.append("SET SQL_SAFE_UPDATES = 0;")
    lines.append("START TRANSACTION;")
    lines.append("")
    lines.append("-- 1. dtb_product_class の価格 (price01, price02) および update_date の更新")
    
    for r in records:
        pid = r['product_id']
        c1 = r['class_category_id1']
        c2 = r['class_category_id2']
        p02 = r['price02']
        p01 = r['price01']
        
        # WHERE句 (規格1、規格2、visible=1)
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
        
        # SET句
        p01_val = f"{p01:.2f}" if p01 is not None else "NULL"
        p02_val = f"{p02:.2f}"
        
        comment = ""
        if r['product_code']:
            comment = f" -- {r['product_code']}"
            if r['product_name']:
                # 長い商品名は省略
                p_name_short = r['product_name'].replace('\n', ' ')[:20]
                comment += f" ({p_name_short})"
                
        lines.append(
            f"UPDATE dtb_product_class SET price01 = {p01_val}, price02 = {p02_val}, update_date = UTC_TIMESTAMP() "
            f"WHERE {where_clause};{comment}"
        )
    
    lines.append("")
    lines.append("-- 2. dtb_product (親商品テーブル) の更新日時 (update_date) を更新")
    chunk_size = 500
    for i in range(0, len(product_ids), chunk_size):
        chunk = product_ids[i:i + chunk_size]
        ids_str = ", ".join(map(str, chunk))
        lines.append(f"UPDATE dtb_product SET update_date = UTC_TIMESTAMP() WHERE id IN ({ids_str});")
        
    lines.append("")
    lines.append("-- 3. コミット & セーフモード復元")
    lines.append("COMMIT;")
    lines.append("SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;")
    lines.append("")
    lines.append("-- ====================================================================")
    lines.append(f"-- 完了 (更新完了後は EC-CUBE のキャッシュクリアを実行してください)")
    lines.append("-- ====================================================================")
    
    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="指示CSVから安全な価格更新SQLを生成するツール")
    parser.add_argument("csv_file", nargs="?", default="product_newprice.csv", help="入力CSVファイルパス (デフォルト: product_newprice.csv)")
    parser.add_argument("-o", "--output", default="update_prices.sql", help="出力SQLファイルパス (デフォルト: update_prices.sql)")
    parser.add_argument("--no-backup-table", action="store_true", help="SQL冒頭のバックアップ用テーブル作成クエリを含めない")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"エラー: 指定されたCSVファイル '{args.csv_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
        
    print("=" * 60)
    print("   EC-CUBE 価格改定 SQL 生成ツール")
    print("=" * 60)
    print(f"[*] 入力CSV: {args.csv_file}")
    
    records, errors, encoding = parse_csv(args.csv_file)
    print(f"    - 検出文字コード: {encoding}")
    print(f"    - 読み込み成功規格数: {len(records)} 件")
    
    comma_count = sum(1 for r in records if r['raw_p02_has_comma'])
    if comma_count > 0:
        print(f"    - [カンマ補正] 金額に「,」が含まれていた行: {comma_count} 件 (自動除去済み)")
    
    price01_count = sum(1 for r in records if r['price01'] is not None)
    print(f"    - 通常価格(price01): 設定あり {price01_count} 件 / NULL {len(records) - price01_count} 件")
    
    unique_products = len(set(r['product_id'] for r in records))
    print(f"    - 更新対象の親商品数 (dtb_product): {unique_products} 件")
    
    if errors:
        print(f"\n[!] スキップされた不正行: {len(errors)} 件")
        for r_num, msg in errors[:5]:
            print(f"    - 行 {r_num}: {msg}")
        if len(errors) > 5:
            print(f"    - ... 他 {len(errors) - 5} 件")
            
    # SQLファイル生成
    output_path = args.output
    include_bk = not args.no_backup_table
    generate_sql(records, output_path, include_backup_table=include_bk)
    
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"\n[+] 更新用SQLファイルを生成しました:")
    print(f"    ファイル名: {output_path} ({file_size_kb:.1f} KB)")
    print(f"    バックアップテーブル作成クエリ: {'含む' if include_bk else '含まない'}")
    print("=" * 60)
    print("【次のステップ（適用手順）】")
    print("1. 生成された SQL ファイルの中身をテキストエディタで確認します。")
    print("2. phpMyAdmin の「インポート」または SQLタブで実行するか、以下のコマンドで実行します:")
    print(f"   mysql -h <ホスト> -u <ユーザー> -p <DB名> < {output_path}")
    print("3. 実行後、EC-CUBEのキャッシュクリアを実行します。")
    print("=" * 60)

if __name__ == '__main__':
    main()

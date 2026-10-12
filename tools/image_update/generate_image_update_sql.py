#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EC-CUBE 商品画像更新 SQL生成スクリプト
指示CSV（EC-CUBE商品CSV形式）の「商品画像」列のみを入力とし、
既存の商品レコードを残したまま、画像カラムのみを更新するSQLファイルを生成します。
直接DBへ接続・書き込みは行わず、SQLファイルの生成に専念するため安全です。

仕様:
  - CSVの「商品画像」はカンマ区切りの文字列としてそのまま1カラムへ保存する。
  - 同一商品IDが複数行ある場合は、**最後の行を採用**し、警告を表示する。
  - 商品画像が空の行はスキップ (既存画像を変更しない)。
  - 商品ごとに dtb_product の画像カラムのみを UPDATE する。
"""

import os
import re
import sys
import csv
import argparse
import unicodedata
from datetime import datetime

INVALID_VALUE = re.compile(r'[\x00-\x1f]')


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


def sql_escape(val):
    """SQL文字列リテラル用エスケープ"""
    return val.replace('\\', '\\\\').replace("'", "''")


def normalize_images(raw):
    """画像文字列を整形する。カンマ区切り文字列はそのまま保存するため、空白のみ除去する。"""
    if raw is None:
        return ''
    raw = unicodedata.normalize('NFKC', str(raw)).strip()
    if INVALID_VALUE.search(raw):
        return None
    return raw


def parse_csv(csv_path):
    """CSVを読み込み、商品ごとの最終画像指定を抽出・検証"""
    encoding = detect_encoding(csv_path)
    products = {}  # product_id -> record (最終行を採用)
    errors = []
    warnings = []
    stats = {'rows': 0, 'empty_rows': 0, 'overwrites': 0}

    with open(csv_path, 'r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip() for c in reader.fieldnames or []]

        for col in ['商品ID', '商品画像']:
            if col not in fieldnames:
                raise ValueError(f"CSVに必要なカラム '{col}' が見つかりません。ヘッダー一覧: {fieldnames}")

        for row_num, row in enumerate(reader, start=2):
            stats['rows'] += 1
            raw_pid = (row.get('商品ID') or '').strip()
            raw_img = row.get('商品画像')
            product_name = (row.get('商品名') or '').strip()

            if not raw_pid or not raw_pid.isdigit():
                errors.append((row_num, f"不正な商品ID: '{raw_pid}'"))
                continue
            product_id = int(raw_pid)

            image_value = normalize_images(raw_img)
            if image_value is None:
                errors.append((row_num, f"商品ID={product_id}: 商品画像に制御文字が含まれています"))
                continue

            if image_value == '':
                stats['empty_rows'] += 1
                continue

            if product_id in products:
                stats['overwrites'] += 1
                warnings.append((row_num, f"商品ID={product_id}: 同一商品IDの複数行を検出しました。最後の行を採用します"))

            products[product_id] = {
                'row_num': row_num,
                'product_id': product_id,
                'product_name': product_name,
                'image_value': image_value,
            }

    return list(products.values()), errors, warnings, stats, encoding


def generate_sql(records, output_sql_path, include_backup_table=True):
    """安全な画像カラム更新SQLを生成"""
    product_ids = sorted(r['product_id'] for r in records)
    today_str = datetime.now().strftime('%Y%m%d_%H%M%S')

    lines = []
    lines.append("-- ====================================================================")
    lines.append("-- EC-CUBE 商品画像一括更新 SQL")
    lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 対象商品数: {len(records)} 件")
    lines.append("-- ====================================================================")
    lines.append("")

    if include_backup_table:
        lines.append("-- --------------------------------------------------------------------")
        lines.append("-- [安全策] 事前バックアップ用テーブル作成クエリ")
        lines.append("-- --------------------------------------------------------------------")
        lines.append(f"CREATE TABLE IF NOT EXISTS `bk_product_image_{today_str}` AS")
        lines.append("SELECT * FROM `dtb_product`;")
        lines.append("")

    lines.append("-- --------------------------------------------------------------------")
    lines.append("-- 更新処理本体 (トランザクション開始)")
    lines.append("-- ※ update_date は UTC_TIMESTAMP() で格納します。")
    lines.append("-- --------------------------------------------------------------------")
    lines.append("SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;")
    lines.append("SET SQL_SAFE_UPDATES = 0;")
    lines.append("START TRANSACTION;")
    lines.append("")
    lines.append("-- 1. dtb_product の画像カラムのみ更新")

    for r in records:
        pid = r['product_id']
        name_short = r['product_name'].replace('\n', ' ')[:20]
        image_value = sql_escape(r['image_value'])
        lines.append(f"UPDATE dtb_product SET product_image = '{image_value}', update_date = UTC_TIMESTAMP() WHERE id = {pid};" + (f" -- {name_short}" if name_short else ""))

    lines.append("")
    lines.append("-- 2. コミット & セーフモード復元")
    lines.append("COMMIT;")
    lines.append("SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;")
    lines.append("")
    lines.append("-- ====================================================================")
    lines.append("-- 完了 (更新完了後は EC-CUBE のキャッシュクリアを実行してください)")
    lines.append("-- ====================================================================")

    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="指示CSVから安全な商品画像更新SQLを生成するツール")
    parser.add_argument("csv_file", nargs="?", default="product_image.csv", help="入力CSVファイルパス (デフォルト: product_image.csv)")
    parser.add_argument("-o", "--output", default="update_images.sql", help="出力SQLファイルパス (デフォルト: update_images.sql)")
    parser.add_argument("--no-backup-table", action="store_true", help="SQL冒頭のバックアップ用テーブル作成クエリを含めない")

    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"エラー: 指定されたCSVファイル '{args.csv_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("   EC-CUBE 商品画像更新 SQL 生成ツール")
    print("=" * 60)
    print(f"[*] 入力CSV: {args.csv_file}")

    try:
        records, errors, warnings, stats, encoding = parse_csv(args.csv_file)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"    - 検出文字コード: {encoding}")
    print(f"    - CSV行数: {stats['rows']} 行 (画像指定なしでスキップ: {stats['empty_rows']} 行)")
    print(f"    - 更新対象商品数: {len(records)} 件")
    if stats['overwrites']:
        print(f"    - [複数行検出] 同一商品IDの後続行: {stats['overwrites']} 件 (最後の行を採用)")

    if warnings:
        print(f"\n[!] 警告: {len(warnings)} 件")
        for r_num, msg in warnings[:5]:
            print(f"    - 行 {r_num}: {msg}")
        if len(warnings) > 5:
            print(f"    - ... 他 {len(warnings) - 5} 件")

    if errors:
        print(f"\n[!] スキップされた不正データ: {len(errors)} 件")
        for r_num, msg in errors[:5]:
            print(f"    - 行 {r_num}: {msg}")
        if len(errors) > 5:
            print(f"    - ... 他 {len(errors) - 5} 件")

    if not records:
        print("\nエラー: 更新対象の画像データがありません。SQLは生成しません。", file=sys.stderr)
        sys.exit(1)

    include_bk = not args.no_backup_table
    generate_sql(records, args.output, include_backup_table=include_bk)

    file_size_kb = os.path.getsize(args.output) / 1024
    print(f"\n[+] 更新用SQLファイルを生成しました:")
    print(f"    ファイル名: {args.output} ({file_size_kb:.1f} KB)")
    print(f"    バックアップテーブル作成クエリ: {'含む' if include_bk else '含まない'}")
    print("=" * 60)
    print("【次のステップ（適用手順）】")
    print("1. 生成された SQL ファイルの中身をテキストエディタで確認します。")
    print("2. phpMyAdmin の「インポート」またはコマンドで実行します:")
    print(f"   mysql -h <ホスト> -u <ユーザー> -p <DB名> < {args.output}")
    print("3. 実行後、EC-CUBEのキャッシュクリアを実行します。")
    print("=" * 60)


if __name__ == '__main__':
    main()

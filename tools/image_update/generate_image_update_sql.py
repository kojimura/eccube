#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EC-CUBE 商品画像更新 SQL生成スクリプト
指示CSV（EC-CUBE商品CSV形式）の「商品画像」列のみを入力とし、
dtb_product_image を商品ID単位で置換(DELETE → INSERT)するSQLファイルを生成します。
直接DBへ接続・書き込みは行わず、SQLファイルの生成に専念するため安全です。

仕様:
  - 「商品画像」列はカンマ区切り (例: "a.png,b.png,c.png")。
    記載順に sort_no = 1, 2, 3... を割り当てます (先頭が1番目に表示)。
  - 同一商品IDが複数行ある場合は最後の行を採用し、警告を表示します。
  - 商品画像が空の行はスキップ (既存画像を変更しない)。
  - dtb_product (商品レコード) 自体は変更しません。
  - dtb_product に存在しない商品IDは DELETE/INSERT とも対象外になります。
"""

import os
import re
import sys
import csv
import argparse
import unicodedata
from datetime import datetime

# ファイル名として許可しない文字 (SQLインジェクション・パス操作対策)
INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def detect_encoding(file_path):
    """CSVの文字コードを判定 (UTF-8 with BOM, UTF-8, CP932/Shift_JIS)"""
    for enc in ['utf-8-sig', 'utf-8', 'cp932', 'euc-jp']:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'


def sql_escape(val):
    """SQL文字列リテラル用エスケープ"""
    return val.replace('\\', '\\\\').replace("'", "''")


def parse_images(raw):
    """カンマ区切りの画像ファイル名を分解。(順序維持・重複除去) -> (files, dup_count, invalid_names)"""
    files = []
    invalid = []
    dup = 0
    if not raw:
        return files, dup, invalid
    raw = unicodedata.normalize('NFKC', raw)
    for name in raw.split(','):
        name = name.strip()
        if not name:
            continue
        if INVALID_FILENAME.search(name):
            invalid.append(name)
            continue
        if name in files:
            dup += 1
            continue
        files.append(name)
    return files, dup, invalid


def parse_csv(csv_path):
    """CSVを読み込み、商品ごとの画像リストを抽出・検証 (同一商品IDは最後の行を採用)"""
    encoding = detect_encoding(csv_path)
    products = {}   # product_id -> record
    errors = []
    warnings = []
    stats = {'rows': 0, 'empty_rows': 0, 'dup_files': 0, 'overwrites': 0}

    with open(csv_path, 'r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip() for c in reader.fieldnames or []]

        for col in ['商品ID', '商品画像']:
            if col not in fieldnames:
                raise ValueError(f"CSVに必要なカラム '{col}' が見つかりません。ヘッダー一覧: {fieldnames}")

        for row_num, row in enumerate(reader, start=2):
            stats['rows'] += 1
            raw_pid = (row.get('商品ID') or '').strip()
            raw_img = row.get('商品画像') or ''
            product_name = (row.get('商品名') or '').strip()

            if not raw_pid or not raw_pid.isdigit():
                errors.append((row_num, f"不正な商品ID: '{raw_pid}'"))
                continue
            product_id = int(raw_pid)

            files, dup, invalid = parse_images(raw_img)
            for bad in invalid:
                errors.append((row_num, f"商品ID={product_id}: 不正な画像ファイル名 '{bad}' (除外)"))

            if not files:
                stats['empty_rows'] += 1
                continue

            if product_id in products:
                stats['overwrites'] += 1
                prev = products[product_id]
                if prev['files'] != files:
                    warnings.append((row_num, f"商品ID={product_id}: 行 {prev['row_num']} の画像指定を行 {row_num} で上書きします (最後の行を採用)"))
                else:
                    warnings.append((row_num, f"商品ID={product_id}: 行 {prev['row_num']} と同一内容の重複行です (最後の行を採用)"))
                stats['dup_files'] -= prev['dup']

            stats['dup_files'] += dup
            products[product_id] = {
                'row_num': row_num,
                'product_id': product_id,
                'product_name': product_name,
                'files': files,
                'dup': dup,
            }

    return list(products.values()), errors, warnings, stats, encoding


def generate_sql(records, output_sql_path, include_backup_table=True):
    """dtb_product_image 置換SQLを生成"""
    today_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    total_images = sum(len(r['files']) for r in records)

    lines = []
    lines.append("-- ====================================================================")
    lines.append("-- EC-CUBE 商品画像一括更新 SQL (dtb_product_image 置換)")
    lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 対象商品数: {len(records)} 件 / 画像総数: {total_images} 件")
    lines.append("-- ====================================================================")
    lines.append("")

    if include_backup_table:
        lines.append("-- --------------------------------------------------------------------")
        lines.append("-- [安全策] 事前バックアップ用テーブル作成クエリ")
        lines.append("-- --------------------------------------------------------------------")
        lines.append(f"CREATE TABLE IF NOT EXISTS `bk_product_image_{today_str}` AS")
        lines.append("SELECT * FROM `dtb_product_image`;")
        lines.append("")

    lines.append("-- --------------------------------------------------------------------")
    lines.append("-- 更新処理本体 (トランザクション開始)")
    lines.append("-- ※ id は AUTO_INCREMENT、create_date は UTC_TIMESTAMP() で格納します。")
    lines.append("-- ※ sort_no は CSV の記載順 (1始まり)。")
    lines.append("-- --------------------------------------------------------------------")
    lines.append("SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;")
    lines.append("SET SQL_SAFE_UPDATES = 0;")
    lines.append("START TRANSACTION;")
    lines.append("")

    for r in records:
        pid = r['product_id']
        name_short = r['product_name'].replace('\n', ' ')[:20]
        lines.append(f"-- 商品ID={pid}" + (f" ({name_short})" if name_short else ""))
        lines.append(
            f"DELETE FROM dtb_product_image WHERE product_id = {pid} "
            f"AND EXISTS (SELECT 1 FROM dtb_product p WHERE p.id = {pid});"
        )
        for sort_no, fname in enumerate(r['files'], start=1):
            lines.append(
                "INSERT INTO dtb_product_image (product_id, creator_id, file_name, sort_no, create_date, discriminator_type) "
                f"SELECT p.id, p.creator_id, '{sql_escape(fname)}', {sort_no}, UTC_TIMESTAMP(), 'productimage' "
                f"FROM dtb_product p WHERE p.id = {pid};"
            )

    lines.append("")
    lines.append("COMMIT;")
    lines.append("SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;")
    lines.append("")
    lines.append("-- ====================================================================")
    lines.append("-- 完了 (更新完了後は EC-CUBE のキャッシュクリアを実行してください)")
    lines.append("-- ※ 画像ファイル自体は html/upload/save_image/ に事前配置してください。")
    lines.append("-- ====================================================================")

    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="指示CSVから商品画像(dtb_product_image)置換SQLを生成するツール")
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
    print(f"    - 更新対象の商品数 (dtb_product_image): {len(records)} 件")
    print(f"    - 登録画像総数: {sum(len(r['files']) for r in records)} 件")
    if stats['dup_files']:
        print(f"    - [重複除去] 同一商品内で重複していた画像名: {stats['dup_files']} 件")
    if stats['overwrites']:
        print(f"    - [複数行検出] 同一商品IDの後続行で上書き: {stats['overwrites']} 件 (最後の行を採用)")

    if warnings:
        print(f"\n[!] 警告: {len(warnings)} 件")
        for r_num, msg in warnings[:10]:
            print(f"    - 行 {r_num}: {msg}")
        if len(warnings) > 10:
            print(f"    - ... 他 {len(warnings) - 10} 件")

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
    print("1. 画像ファイルを html/upload/save_image/ に配置します。")
    print("2. 生成された SQL ファイルの中身をテキストエディタで確認します。")
    print("3. phpMyAdmin の「インポート」またはコマンドで実行します:")
    print(f"   mysql -h <ホスト> -u <ユーザー> -p <DB名> < {args.output}")
    print("4. 実行後、EC-CUBEのキャッシュクリアを実行します。")
    print("=" * 60)


if __name__ == '__main__':
    main()

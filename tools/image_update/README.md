# EC-CUBE 商品画像更新

## 概要
EC-CUBE管理画面の「商品CSV登録」で規格商品を取り込むと商品IDが分裂してしまう問題を回避し、
**既存の商品レコードを残したまま、商品画像のカンマ区切り文字列だけを上書きする**ためのSQLを生成する。(`price_update` と同じ方式)

```
[指示CSV] (product_image.csv)
   │
   ▼
[Pythonスクリプト] (generate_image_update_sql.py)
   │  ・文字コード判定
   │  ・同一商品IDは最後の行を採用
   │  ・同一商品IDが複数行ある場合は警告を表示
   │  ・事前バックアップテーブル作成クエリ付き
   │  ・日時は UTC_TIMESTAMP() で格納
   │
   ▼
[更新用SQL] (update_images.sql)
   │
   ├─► phpMyAdmin でインポート実行
   └─► コマンドライン (mysql) で実行
   │
   ▼
[EC-CUBE キャッシュクリア]
```

---

## 1. ファイル構成
- `generate_image_update_sql.py` : 指示CSVから更新用SQLを生成するPythonツール
- `product_image.csv` : 画像更新の指示CSVファイル (EC-CUBE商品CSV形式)
- `update_images.sql` : 生成された実行用SQLファイル (スクリプト実行で生成)

---

## 2. 入力CSVの仕様
必須カラムは `商品ID` と `商品画像` のみ。その他の列は無視される。

- `商品画像` : カンマ区切りの文字列をそのまま1フィールドへ保存する。
- 同一商品IDの行が複数ある場合は、**最後の行を採用**する。
- 同一商品IDの複数行は**警告を表示**する。
- `商品画像` が空の行は**スキップ** (既存画像は変更されない)。
- `商品画像` に制御文字が含まれる場合はエラーとして除外する。

---

## 3. SQLファイルの安全設計
1. **事前バックアップテーブルの自動作成**
   `dtb_product` 全体を `bk_product_image_YYYYMMDD_HHMMSS` に退避する。
2. **既存商品レコードを維持**
   `dtb_product` の `product_image` と `update_date` のみを更新し、他のフィールドには一切触れない。
3. **トランザクション保護**
   `START TRANSACTION;` 〜 `COMMIT;` で囲む。
4. **更新方式は商品単位の上書き**
   CSVの `商品画像` をそのまま `product_image` カラムに保存する。
   複数画像はカンマ区切り文字列のまま1カラムに保持される。
5. **日時の UTC 統一**
   `update_date` は `UTC_TIMESTAMP()` を使用する。
6. **SQLエスケープ**
   画像文字列中の `'` や `\` はエスケープされる。

> 注意: 画像ファイル自体は `html/upload/save_image/` に事前配置すること。

---

## 4. 手順

### ステップ1: SQLファイルの生成
```bash
python3 generate_image_update_sql.py product_image.csv -o update_images.sql
```
バックアップテーブルが不要な場合は `--no-backup-table` を付ける。

### ステップ2: 生成されたSQLの確認
テキストエディタ等で `update_images.sql` の内容を確認する。

### ステップ3: データベースへの適用

#### パターンA: phpMyAdmin を使用する場合
1. 対象の EC-CUBE データベースを選択する。
2. 上部メニューの **「インポート」** タブで `update_images.sql` を選択し **「実行」** をクリックする。

#### パターンB: コマンドライン (mysql) を使用する場合
```bash
mysql -h <ホスト> -u <ユーザー名> -p <データベース名> < update_images.sql
```

### ステップ4: EC-CUBEのキャッシュクリア
- **管理画面**: 「コンテンツ管理 > キャッシュ管理」から削除
- **コマンド**: `bin/console cache:clear --no-debug`

---

## 5. ロールバック手順
冒頭で作成されたバックアップテーブルから `dtb_product` を復元する。

```sql
START TRANSACTION;
DELETE FROM dtb_product;
INSERT INTO dtb_product SELECT * FROM bk_product_image_YYYYMMDD_HHMMSS;
COMMIT;
```
※バックアップテーブル名は実行日時によって異なるため、生成されたSQLの冒頭を確認すること。

---

## 6. 修正履歴
- 2026-10-12: 商品画像のカンマ区切り文字列を `dtb_product.product_image` へ上書きする方式に修正。
- 2026-10-12: 初版作成 (`price_update` を踏襲し、商品画像のみを更新するSQL生成ツールを追加)。

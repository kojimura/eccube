# EC-CUBE 商品画像更新

## 概要
EC-CUBE管理画面の「商品CSV登録」で規格商品を取り込むと商品IDが分裂してしまう問題を回避し、
**商品画像のみ**を本番DBへ安全に更新するためのSQLを生成する。(`price_update` と同じ方式)

```
[指示CSV] (product_image.csv)
   │
   ▼
[Pythonスクリプト] (generate_image_update_sql.py)
   │  ・文字コード判定
   │  ・規格ごとの行を商品ID単位に集約
   │  ・画像名の重複除去 / 不正文字チェック
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

- `商品画像` : カンマ区切りで複数指定 (例: `"cube-1.png,cube-2.png,cube-3.png"`)。記載順が表示順 (`sort_no` = 1始まり) になる。
- 規格商品は規格ごとに行が分かれるが、**同一商品IDの行は1商品に集約**される。
  (画像指定が異なる場合は最初の行を採用し、警告を表示)
- `商品画像` が空の行は**スキップ** (既存画像は変更されない)。
- 同一商品内で同じファイル名が重複している場合は、重複を除去する。
- ファイル名に `\ / : * ? " < > |` や制御文字が含まれる場合はエラーとして除外する。

---

## 3. SQLファイルの安全設計
1. **事前バックアップテーブルの自動作成**
   `dtb_product_image` 全体を `bk_product_image_YYYYMMDD_HHMMSS` に退避する。
2. **商品IDの分裂防止**
   商品IDを指定して `dtb_product_image` のみを操作するため、商品IDが新規作成されたり分裂したりしない。
   `dtb_product_class` (価格・在庫・規格) には一切触れない。
3. **トランザクション保護**
   `START TRANSACTION;` 〜 `COMMIT;` で囲む。
4. **更新方式は商品単位の置換**
   対象商品の既存画像を `DELETE` した後、CSVの順序で `INSERT` する。
   `creator_id` は `dtb_product.creator_id` から取得し、存在しない商品IDの場合は何も挿入されない。
5. **日時の UTC 統一**
   `create_date` / `update_date` は `UTC_TIMESTAMP()` を使用する。
6. **SQLエスケープ**
   ファイル名中の `'` や `\` はエスケープされる。

> 注意: 画像を「置換」する仕様のため、CSVに記載のない既存画像はその商品から外れる。
> 画像ファイル自体は `html/upload/save_image/` に事前配置すること。

---

## 4. 手順

### ステップ1: SQLファイルの生成
```bash
python3 generate_image_update_sql.py product_image.csv -o update_images.sql
```
バックアップテーブルが不要な場合は `--no-backup-table` を付ける。

### ステップ2: 画像ファイルの配置
`html/upload/save_image/` にCSVで指定した画像ファイルをアップロードする。

### ステップ3: 生成されたSQLの確認
テキストエディタ等で `update_images.sql` の内容を確認する。

### ステップ4: データベースへの適用

#### パターンA: phpMyAdmin を使用する場合
1. 対象の EC-CUBE データベースを選択する。
2. 上部メニューの **「インポート」** タブで `update_images.sql` を選択し **「実行」** をクリックする。

#### パターンB: コマンドライン (mysql) を使用する場合
```bash
mysql -h <ホスト> -u <ユーザー名> -p <データベース名> < update_images.sql
```

### ステップ5: EC-CUBEのキャッシュクリア
- **管理画面**: 「コンテンツ管理 > キャッシュ管理」から削除
- **コマンド**: `bin/console cache:clear --no-debug`

---

## 5. ロールバック手順
冒頭で作成されたバックアップテーブルから `dtb_product_image` を復元する。

```sql
START TRANSACTION;
DELETE FROM dtb_product_image;
INSERT INTO dtb_product_image SELECT * FROM bk_product_image_YYYYMMDD_HHMMSS;
COMMIT;
```
※バックアップテーブル名は実行日時によって異なるため、生成されたSQLの冒頭を確認すること。

---

## 6. 修正履歴
- 2026-10-12: 初版作成 (`price_update` を踏襲し、商品画像のみを更新するSQL生成ツールを追加)。

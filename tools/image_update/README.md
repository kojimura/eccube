# EC-CUBE 商品画像更新

## 概要
EC-CUBE管理画面の「商品CSV登録」で規格商品を取り込むと商品IDが分裂してしまう問題を回避し、
**商品レコード(`dtb_product`)は変更せず、商品画像テーブル(`dtb_product_image`)のみ**を
商品ID単位で置換するSQLを生成する。(`price_update` と同じ方式)

```
[指示CSV] (product_image.csv)
   │
   ▼
[Pythonスクリプト] (generate_image_update_sql.py)
   │  ・文字コード判定
   │  ・同一商品IDが複数行ある場合は最初の行を採用し、以降は無視
   │  ・カンマ区切りを先頭から sort_no=1,2,3... に展開
   │  ・画像名の重複除去 / 不正文字チェック
   │  ・事前バックアップテーブル作成クエリ付き
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

## 2. 対象テーブル `dtb_product_image`

| カラム | 登録内容 |
|---|---|
| id | AUTO_INCREMENT (指定しない) |
| product_id | CSVの商品ID |
| creator_id | `dtb_product.creator_id` を引き継ぎ |
| file_name | 画像ファイル名 |
| sort_no | CSVの記載順 (先頭=1) |
| create_date | `UTC_TIMESTAMP()` |
| discriminator_type | `productimage` |

---

## 3. 入力CSVの仕様
必須カラムは `商品ID` と `商品画像` のみ。その他の列は無視される。

- `商品画像` : カンマ区切りで複数指定 (例: `"cube-1.png,cube-2.png,cube-3.png"`)。**先頭から順に表示**される (`sort_no` = 1始まり)。
- 規格商品は規格ごとに行が分かれるが、**同一商品IDが複数行ある場合は最初の行を採用**し、残りは無視する。
- 無視した行は**警告を表示**する。
- `商品画像` が空の行は**スキップ** (既存画像は変更されない)。
- 同一商品内で同じファイル名が重複している場合は、重複を除去する。
- ファイル名に `\ / : * ? " < > |` や制御文字が含まれる場合はエラーとして除外する。

---

## 4. SQLファイルの安全設計
1. **事前バックアップテーブルの自動作成**
   `dtb_product_image` 全体を `bk_product_image_YYYYMMDD_HHMMSS` に退避する。
2. **商品レコードは変更しない**
   `dtb_product` / `dtb_product_class` (価格・在庫・規格) には一切書き込まない。
3. **存在しない商品IDは対象外**
   `dtb_product` に存在しない商品IDは DELETE も INSERT も行われない。
4. **トランザクション保護**
   `START TRANSACTION;` 〜 `COMMIT;` で囲む。
5. **更新方式は商品単位の置換**
   対象商品の既存画像を `DELETE` した後、CSVの順序で `INSERT` する。
6. **日時の UTC 統一**
   `create_date` は `UTC_TIMESTAMP()` を使用する。
7. **SQLエスケープ**
   ファイル名中の `'` や `\` はエスケープされる。

> 注意: 画像を「置換」する仕様のため、CSVに記載のない既存画像はその商品から外れる。
> 画像ファイル自体は `html/upload/save_image/` に事前配置すること。

---

## 5. 手順

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

Docker 環境の例:
```bash
docker exec -i ec-cube-mysql-1 mysql -u root -proot eccubedb < update_images.sql
```

### ステップ5: 結果確認
```bash
docker exec -it ec-cube-mysql-1 mysql -u root -proot eccubedb -e "SELECT product_id, file_name, sort_no FROM dtb_product_image ORDER BY product_id, sort_no;"
```

### ステップ6: EC-CUBEのキャッシュクリア
- **管理画面**: 「コンテンツ管理 > キャッシュ管理」から削除
- **コマンド**: `bin/console cache:clear --no-debug`

---

## 6. ロールバック手順
冒頭で作成されたバックアップテーブルから `dtb_product_image` を復元する。

```sql
START TRANSACTION;
DELETE FROM dtb_product_image;
INSERT INTO dtb_product_image SELECT * FROM bk_product_image_YYYYMMDD_HHMMSS;
COMMIT;
```
※バックアップテーブル名は実行日時によって異なるため、生成されたSQLの冒頭を確認すること。

---

## 7. 修正履歴
- 2026-10-12: 同一商品IDの複数行は最初の行を採用し、後続行は警告して無視する方式に変更。
- 2026-10-12: `dtb_product.product_image` が存在しない(Unknown column)ため、`dtb_product_image` を商品ID単位で DELETE → INSERT する方式に修正。
- 2026-10-12: 初版作成。

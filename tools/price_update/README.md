# EC-CUBE 商品価格改定

## 概要
EC-CUBE管理画面の「商品CSV登録」で規格商品を取り込むと商品IDが分裂してしまう問題を回避し、
本番DBを安全に更新する

```
[指示CSV] (product_newprice.csv)
   │
   ▼
[Pythonスクリプト] (generate_price_update_sql.py)
   │  ・文字コード判定 / カンマ付き金額の自動除去
   │  ・規格ごとの一意特定 (visible=1)
   │  ・事前バックアップテーブル作成クエリ付き
   │  ・update_date は UTC_TIMESTAMP() で格納（EC-CUBE の UTC 前提に合わせる）
   │
   ▼
[更新用SQL] (update_prices.sql)
   │
   ├─► phpMyAdmin でインポート実行
   └─► コマンドライン (mysql) で実行
   │
   ▼
[EC-CUBE キャッシュクリア]
```

---

## 1. ファイル構成
- `generate_price_update_sql.py` : 指示CSVから更新用SQLを生成するPythonツール
- `product_newprice.csv` : 価格改定の指示CSVファイル
- `update_prices.sql` : 生成された実行用SQLファイル (約290KB, 1,279規格対象)

---

## 2. SQLファイルの安全設計
1. **事前バックアップテーブルの自動作成**
   更新直前の規格価格データを退避するテーブル（`bk_product_class_price_YYYYMMDD_HHMMSS`）を自動作成します。
   万一元の状態に戻したい場合も1クエリで復元可能です。
2. **商品IDの分裂防止**
   各規格の条件 (`product_id` + `規格1` + `規格2` + `visible = 1`) をSQLのWHERE句でピンポイントに指定して更新するため、商品IDが新しく作成されたり分裂したりしません。
3. **トランザクション保護**
   `START TRANSACTION;` 〜 `COMMIT;` で囲まれており、構文エラーなどが発生した場合は自動的に全件ロールバックされます。
4. **金額カンマ除去**
   CSV内に含まれる `15,900` などのカンマ付き数値を自動で `15900.00` に正規化しています。
5. **日時の UTC 統一**
   `update_date` は `NOW()` ではなく `UTC_TIMESTAMP()` を使って保存します。
   EC-CUBE は DB の日時を UTC として扱うため、JST のまま保存すると表示時に 9 時間ずれるのを防げます。

---

## 3. 商品CSV登録のフォーマット（CSV出力項目設定）
1. A	商品ID
2. B	公開ステータス(ID)
3. C	商品名
4. D	ショップ用メモ欄
5. E	商品説明(一覧)
6. F	商品説明(詳細)
7. G	検索ワード
8. H	フリーエリア
9. I	商品画像
10. J	商品カテゴリ(ID)
11. K	タグ(ID)
12. L	販売種別(ID)
13. M	規格分類1(ID)
14. N	規格分類2(ID)
15. O	発送日目安(ID)
16. P	商品コード
17. Q	在庫数
18. R	在庫数無制限フラグ
19. S	販売制限数
20. T	通常価格
21. U	販売価格
22. V	送料
23. W	税率
24. X	商品規格表示フラグ 

---

## 4. 手順

### ステップ1: SQLファイルの生成 (必要な場合)
CSVを更新・差し替えた場合は、以下のコマンドでSQLを再生成します。
```bash
python3 generate_price_update_sql.py product_newprice.csv -o update_prices.sql
```

### ステップ2: 生成されたSQLの確認
テキストエディタ等で `update_prices.sql` の内容を確認します。

### ステップ3: データベースへの適用

#### パターンA: phpMyAdmin を使用する場合
1. phpMyAdmin にログインし、対象の EC-CUBE データベースを選択します。
2. 上部メニューの **「インポート」** タブをクリックします。
3. 「アップロードファイル」の「ファイルを選択」で `update_prices.sql` を選択します。
4. ページ最下部の **「実行」** をクリックします。
   (※「SQL」タブを開き、ファイルの内容を貼り付けて実行しても同様です)

#### パターンB: サーバーのコマンドライン (mysql) を使用する場合
```bash
mysql -h <ホスト> -u <ユーザー名> -p <データベース名> < update_prices.sql
```

### ステップ4: EC-CUBEのキャッシュクリア
DB更新後は、商品情報のキャッシュをクリアしてサイト表示を最新化します。
- **管理画面**: 「コンテンツ管理 > キャッシュ管理」から削除
- **コマンド**: `bin/console cache:clear --no-debug`

---

## 5. ロールバック手順 (万一元の価格に戻したい場合)
冒頭で作成されたバックアップテーブルから、元の価格・更新日時に一括復元できます。

```sql
UPDATE dtb_product_class pc
INNER JOIN bk_product_class_price_20261004_071356 bk ON pc.id = bk.id
SET pc.price01 = bk.price01,
    pc.price02 = bk.price02,
    pc.update_date = bk.update_date;
```
※バックアップテーブル名は実行日時によって異なりますので、生成されたSQLの冒頭を確認してください。

---

## 6. 修正履歴
- 2026-10-10: テストガイドの期待値説明を UTC 前提に修正。
- 2026-10-10: `update_date` の更新を `NOW()` から `UTC_TIMESTAMP()` に変更。EC-CUBE が日時を UTC として扱う前提に合わせ、9時間ずれを防止。

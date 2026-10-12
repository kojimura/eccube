-- ====================================================================
-- EC-CUBE 商品価格一括改定 SQL
-- 生成日時: 2026-10-12 14:50:39
-- 対象件数: 8 規格 (親商品数: 3 件)
-- ====================================================================

-- --------------------------------------------------------------------
-- [安全策] 事前バックアップ用テーブル作成クエリ
-- 実行しておくと、万一元に戻したい場合に一瞬でロールバック可能です。
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `bk_product_class_price_20261012_145039` AS
SELECT `id`, `product_id`, `class_category_id1`, `class_category_id2`, `price01`, `price02`, `update_date`
FROM `dtb_product_class`;

-- --------------------------------------------------------------------
-- 更新処理本体 (トランザクション開始)
-- ※ EC-CUBE は DB の日時を UTC として扱うため、update_date は UTC_TIMESTAMP() で格納します。
-- --------------------------------------------------------------------
SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;
SET SQL_SAFE_UPDATES = 0;
START TRANSACTION;

-- 1. dtb_product_class の価格 (price02) および update_date の更新
UPDATE dtb_product_class SET price02 = 100.00, update_date = UTC_TIMESTAMP() WHERE product_id = 103 AND class_category_id1 = 1 AND class_category_id2 = 4 AND visible = 1; -- TEST-COLOR-S-RED ([テスト] 規格あり商品(2軸規格))
UPDATE dtb_product_class SET price02 = 110.00, update_date = UTC_TIMESTAMP() WHERE product_id = 103 AND class_category_id1 = 1 AND class_category_id2 = 5 AND visible = 1; -- TEST-COLOR-S-BLU ([テスト] 規格あり商品(2軸規格))
UPDATE dtb_product_class SET price02 = 120.00, update_date = UTC_TIMESTAMP() WHERE product_id = 103 AND class_category_id1 = 2 AND class_category_id2 = 4 AND visible = 1; -- TEST-COLOR-M-RED ([テスト] 規格あり商品(2軸規格))
UPDATE dtb_product_class SET price02 = 130.00, update_date = UTC_TIMESTAMP() WHERE product_id = 103 AND class_category_id1 = 2 AND class_category_id2 = 5 AND visible = 1; -- TEST-COLOR-M-BLU ([テスト] 規格あり商品(2軸規格))
UPDATE dtb_product_class SET price02 = 140.00, update_date = UTC_TIMESTAMP() WHERE product_id = 103 AND class_category_id1 = 2 AND class_category_id2 = 6 AND visible = 1; -- TEST-COLOR-M-DISCONTINUED ([テスト] 規格あり商品(2軸規格))
UPDATE dtb_product_class SET price02 = 150.00, update_date = UTC_TIMESTAMP() WHERE product_id = 102 AND class_category_id1 = 1 AND class_category_id2 IS NULL AND visible = 1; -- TEST-SIZE-S ([テスト] 規格あり商品(単一規格))
UPDATE dtb_product_class SET price02 = 160.00, update_date = UTC_TIMESTAMP() WHERE product_id = 102 AND class_category_id1 = 2 AND class_category_id2 IS NULL AND visible = 1; -- TEST-SIZE-M ([テスト] 規格あり商品(単一規格))
UPDATE dtb_product_class SET price02 = 170.00, update_date = UTC_TIMESTAMP() WHERE product_id = 101 AND class_category_id1 IS NULL AND class_category_id2 IS NULL AND visible = 1; -- TEST-SINGLE-001 ([テスト] 規格なし商品)

-- 2. dtb_product (親商品テーブル) の更新日時 (update_date) を更新
UPDATE dtb_product SET update_date = UTC_TIMESTAMP() WHERE id IN (101, 102, 103);

-- 3. コミット & セーフモード復元
COMMIT;
SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;

-- ====================================================================
-- 完了 (更新完了後は EC-CUBE のキャッシュクリアを実行してください)
-- ====================================================================
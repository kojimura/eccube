-- ====================================================================
-- EC-CUBE 価格改定機能テスト用: テーブル作成 & 初期データ (変更前) 投入SQL
-- 対象商品ID: 101 (規格なし), 102 (単一規格), 103 (2軸規格)
-- ====================================================================

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------------------
-- 1. テーブル作成 (存在しない場合のみ作成)
-- --------------------------------------------------------------------

-- 1-1. dtb_product (親商品テーブル)
CREATE TABLE IF NOT EXISTS `dtb_product` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `product_status_id` smallint(5) unsigned DEFAULT 1,
  `name` varchar(255) NOT NULL,
  `note` longtext DEFAULT NULL,
  `description_list` longtext DEFAULT NULL,
  `description_detail` longtext DEFAULT NULL,
  `search_word` longtext DEFAULT NULL,
  `free_area` longtext DEFAULT NULL,
  `create_date` datetime NOT NULL,
  `update_date` datetime NOT NULL,
  `discriminator_type` varchar(255) NOT NULL DEFAULT 'product',
  `display_rank` int(11) NOT NULL DEFAULT 0,
  `free_description_about_quantity` longtext DEFAULT NULL,
  `free_description_about_selling_price` longtext DEFAULT NULL,
  `free_description_of_payment_delivery` longtext DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 1-2. dtb_product_class (商品規格・価格テーブル)
CREATE TABLE IF NOT EXISTS `dtb_product_class` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `sale_type_id` smallint(5) unsigned DEFAULT 1,
  `class_category_id1` int(10) unsigned DEFAULT NULL,
  `class_category_id2` int(10) unsigned DEFAULT NULL,
  `delivery_duration_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `product_code` varchar(255) DEFAULT NULL,
  `stock` decimal(10,0) DEFAULT NULL,
  `stock_unlimited` tinyint(1) NOT NULL DEFAULT 0,
  `sale_limit` decimal(10,0) unsigned DEFAULT NULL,
  `price01` decimal(12,2) DEFAULT NULL,
  `price02` decimal(12,2) NOT NULL,
  `delivery_fee` decimal(12,2) unsigned DEFAULT NULL,
  `visible` tinyint(1) NOT NULL DEFAULT 1,
  `create_date` datetime NOT NULL,
  `update_date` datetime NOT NULL,
  `currency_code` varchar(255) DEFAULT 'JPY',
  `point_rate` decimal(10,0) unsigned DEFAULT NULL,
  `discriminator_type` varchar(255) NOT NULL DEFAULT 'productclass',
  `regular_discount_id` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_1A11D1BA4584665A` (`product_id`),
  KEY `IDX_1A11D1BA248D128` (`class_category_id1`),
  KEY `IDX_1A11D1BA9B418092` (`class_category_id2`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- --------------------------------------------------------------------
-- 2. テストデータのクリーンアップ (再実行可能にするための削除)
-- --------------------------------------------------------------------
DELETE FROM `dtb_product_class` WHERE `product_id` IN (101, 102, 103);
DELETE FROM `dtb_product` WHERE `id` IN (101, 102, 103);

-- --------------------------------------------------------------------
-- 3. 親商品データ投入 (dtb_product)
-- --------------------------------------------------------------------
INSERT INTO `dtb_product` (
  `id`, `name`, `product_status_id`, `create_date`, `update_date`, `discriminator_type`
) VALUES
(101, '[テスト] 規格なし商品', 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'product'),
(102, '[テスト] 規格あり商品(単一規格)', 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'product'),
(103, '[テスト] 規格あり商品(2軸規格)', 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'product');

-- --------------------------------------------------------------------
-- 4. 規格データ投入 (dtb_product_class: 改定前の初期価格データ)
-- --------------------------------------------------------------------
INSERT INTO `dtb_product_class` (
  `id`, `product_id`, `sale_type_id`, `class_category_id1`, `class_category_id2`,
  `product_code`, `stock`, `stock_unlimited`, `price01`, `price02`, `visible`,
  `create_date`, `update_date`, `currency_code`, `discriminator_type`
) VALUES
-- ====================================================================
-- 【商品1】商品ID: 101 (規格なし商品)
--  変更前: 通常価格 1,300円 / 販売価格 1,000円
--  改定後: 通常価格 1,500円 / 販売価格 1,200円 (CSV指示)
-- ====================================================================
(1001, 101, 1, NULL, NULL, 'TEST-SINGLE-001', 50, 0, 1300.00, 1000.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),

-- ====================================================================
-- 【商品2】商品ID: 102 (単一規格商品: サイズ S / M)
--  規格1=1(S) 変更前: 通常価格 2,200円 / 販売価格 1,800円 -> 改定後: 2,500円 / 2,000円
--  規格1=2(M) 変更前: 通常価格 2,500円 / 販売価格 2,000円 -> 改定後: 2,800円 / 2,300円
-- ====================================================================
(1002, 102, 1, 1, NULL, 'TEST-SIZE-S', 20, 0, 2200.00, 1800.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),
(1003, 102, 1, 2, NULL, 'TEST-SIZE-M', 15, 0, 2500.00, 2000.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),

-- ====================================================================
-- 【商品3】商品ID: 103 (2軸規格商品: サイズ S/M × カラー RED/BLU)
--  規格1=1, 規格2=4(S/16mm × 16mm) 変更前: 通常 NULL / 販売 2,800円 -> 改定後: 通常 NULL / 販売 3,000円
--  規格1=1, 規格2=5(S/32mm × 32mm) 変更前: 通常 NULL / 販売 2,800円 -> 改定後: 通常 NULL / 販売 3,000円
--  規格1=2, 規格2=4(M/16mm × 16mm) 変更前: 通常 3,800円 / 販売 3,200円 -> 改定後: 通常 4,000円 / 販売 3,500円
--  規格1=2, 規格2=5(M/32mm × 32mm) 変更前: 通常 3,800円 / 販売 3,200円 -> 改定後: 通常 4,000円 / 販売 3,500円
-- ====================================================================
(1004, 103, 1, 1, 4, 'TEST-COLOR-S-RED', 10, 0, NULL, 2800.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),
(1005, 103, 1, 1, 5, 'TEST-COLOR-S-BLU', 10, 0, NULL, 2800.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),
(1006, 103, 1, 2, 4, 'TEST-COLOR-M-RED', 8, 0, 3800.00, 3200.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),
(1007, 103, 1, 2, 5, 'TEST-COLOR-M-BLU', 8, 0, 3800.00, 3200.00, 1, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass'),

-- ====================================================================
-- 【検証用オマケ】非表示規格 (visible = 0: 廃盤等のため価格更新されないことの検証用)
-- ====================================================================
(1008, 103, 1, 2, 6, 'TEST-COLOR-M-DISCONTINUED', 0, 0, 9999.00, 9999.00, 0, '2026-01-01 10:00:00', '2026-01-01 10:00:00', 'JPY', 'productclass');

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;

-- ====================================================================
-- 投入データ確認用 SELECT クエリ (実行して初期データを確認できます)
-- ====================================================================
SELECT 
  pc.id AS `規格ID`,
  pc.product_id AS `商品ID`,
  p.name AS `商品名`,
  pc.product_code AS `コード`,
  pc.class_category_id1 AS `規格1`,
  pc.class_category_id2 AS `規格2`,
  pc.price01 AS `変更前通常価格`,
  pc.price02 AS `変更前販売価格`,
  pc.visible AS `表示`,
  pc.update_date AS `更新日時`
FROM dtb_product_class pc
LEFT JOIN dtb_product p ON pc.product_id = p.id
WHERE pc.product_id IN (101, 102, 103)
ORDER BY pc.product_id, pc.id;

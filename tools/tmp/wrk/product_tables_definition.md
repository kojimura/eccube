# 商品マスタ(product)関連テーブル定義

バックアップファイル: `kinen_DB_bkup_202610032013.sql`
EC-CUBE 4系ベース

---

## 特記事項（独自拡張・プラグイン追加カラム）
- **`dtb_product`**:
  - `display_rank` (表示順プラグイン等)
  - `free_description_about_quantity` (数量に関する説明フリー欄)
  - `free_description_about_selling_price` (販売価格に関する説明フリー欄)
  - `free_description_of_payment_delivery` (支払・配送に関する説明フリー欄)
- **`dtb_product_class`**:
  - `regular_discount_id` (定期購入プラグイン `plg_eccube_payment_lite42` 連携)

---

## 1. 商品コアテーブル

### `dtb_product`（商品基本情報）
```sql
CREATE TABLE `dtb_product` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `product_status_id` smallint(5) unsigned DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `note` longtext DEFAULT NULL,
  `description_list` longtext DEFAULT NULL,
  `description_detail` longtext DEFAULT NULL,
  `search_word` longtext DEFAULT NULL,
  `free_area` longtext DEFAULT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  `display_rank` int(11) NOT NULL DEFAULT 0,
  `free_description_about_quantity` longtext DEFAULT NULL,
  `free_description_about_selling_price` longtext DEFAULT NULL,
  `free_description_of_payment_delivery` longtext DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_C49DE22F61220EA6` (`creator_id`),
  KEY `IDX_C49DE22F557B630` (`product_status_id`),
  CONSTRAINT `FK_C49DE22F557B630` FOREIGN KEY (`product_status_id`) REFERENCES `mtb_product_status` (`id`),
  CONSTRAINT `FK_C49DE22F61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2106 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_product_class`（商品規格・価格・商品コード）
```sql
CREATE TABLE `dtb_product_class` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `sale_type_id` smallint(5) unsigned DEFAULT NULL,
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
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `currency_code` varchar(255) DEFAULT NULL,
  `point_rate` decimal(10,0) unsigned DEFAULT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  `regular_discount_id` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_1A11D1BA4584665A` (`product_id`),
  KEY `IDX_1A11D1BAB0524E01` (`sale_type_id`),
  KEY `IDX_1A11D1BA248D128` (`class_category_id1`),
  KEY `IDX_1A11D1BA9B418092` (`class_category_id2`),
  KEY `IDX_1A11D1BABA4269E` (`delivery_duration_id`),
  KEY `IDX_1A11D1BA61220EA6` (`creator_id`),
  KEY `dtb_product_class_price02_idx` (`price02`),
  KEY `dtb_product_class_stock_stock_unlimited_idx` (`stock`,`stock_unlimited`),
  KEY `IDX_1A11D1BA86AEDC4C` (`regular_discount_id`),
  CONSTRAINT `FK_1A11D1BA248D128` FOREIGN KEY (`class_category_id1`) REFERENCES `dtb_class_category` (`id`),
  CONSTRAINT `FK_1A11D1BA4584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_1A11D1BA61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`),
  CONSTRAINT `FK_1A11D1BA86AEDC4C` FOREIGN KEY (`regular_discount_id`) REFERENCES `plg_eccube_payment_lite42_regular_count_discount` (`id`),
  CONSTRAINT `FK_1A11D1BA9B418092` FOREIGN KEY (`class_category_id2`) REFERENCES `dtb_class_category` (`id`),
  CONSTRAINT `FK_1A11D1BAB0524E01` FOREIGN KEY (`sale_type_id`) REFERENCES `mtb_sale_type` (`id`),
  CONSTRAINT `FK_1A11D1BABA4269E` FOREIGN KEY (`delivery_duration_id`) REFERENCES `dtb_delivery_duration` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=506489 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_product_stock`（規格別 在庫管理）
```sql
CREATE TABLE `dtb_product_stock` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_class_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `stock` decimal(10,0) DEFAULT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_BC6C9E4521B06187` (`product_class_id`),
  KEY `IDX_BC6C9E4561220EA6` (`creator_id`),
  CONSTRAINT `FK_BC6C9E4521B06187` FOREIGN KEY (`product_class_id`) REFERENCES `dtb_product_class` (`id`),
  CONSTRAINT `FK_BC6C9E4561220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=63140 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_product_image`（商品画像）
```sql
CREATE TABLE `dtb_product_image` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `file_name` varchar(255) NOT NULL,
  `sort_no` smallint(5) unsigned NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_3267CC7A4584665A` (`product_id`),
  KEY `IDX_3267CC7A61220EA6` (`creator_id`),
  CONSTRAINT `FK_3267CC7A4584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_3267CC7A61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1832 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_product_category`（商品 × カテゴリ 中間テーブル）
```sql
CREATE TABLE `dtb_product_category` (
  `product_id` int(10) unsigned NOT NULL,
  `category_id` int(10) unsigned NOT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`product_id`,`category_id`),
  KEY `IDX_B05778914584665A` (`product_id`),
  KEY `IDX_B057789112469DE2` (`category_id`),
  CONSTRAINT `FK_B057789112469DE2` FOREIGN KEY (`category_id`) REFERENCES `dtb_category` (`id`),
  CONSTRAINT `FK_B05778914584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_product_tag`（商品 × タグ 中間テーブル）
```sql
CREATE TABLE `dtb_product_tag` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `tag_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_4433E7214584665A` (`product_id`),
  KEY `IDX_4433E721BAD26311` (`tag_id`),
  KEY `IDX_4433E72161220EA6` (`creator_id`),
  CONSTRAINT `FK_4433E7214584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_4433E72161220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`),
  CONSTRAINT `FK_4433E721BAD26311` FOREIGN KEY (`tag_id`) REFERENCES `dtb_tag` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

---

## 2. 規格・分類・ステータス関連テーブル

### `dtb_class_name`（規格名）
```sql
CREATE TABLE `dtb_class_name` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `backend_name` varchar(255) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `sort_no` int(10) unsigned NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_187C95AD61220EA6` (`creator_id`),
  CONSTRAINT `FK_187C95AD61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_class_category`（規格分類）
```sql
CREATE TABLE `dtb_class_category` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `class_name_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `backend_name` varchar(255) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `sort_no` int(10) unsigned NOT NULL,
  `visible` tinyint(1) NOT NULL DEFAULT 1,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_9B0D1DBAB462FB2A` (`class_name_id`),
  KEY `IDX_9B0D1DBA61220EA6` (`creator_id`),
  CONSTRAINT `FK_9B0D1DBA61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`),
  CONSTRAINT `FK_9B0D1DBAB462FB2A` FOREIGN KEY (`class_name_id`) REFERENCES `dtb_class_name` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_category`（商品カテゴリ）
```sql
CREATE TABLE `dtb_category` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `parent_category_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `category_name` varchar(255) NOT NULL,
  `hierarchy` int(10) unsigned NOT NULL,
  `sort_no` int(11) NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_5ED2C2B796A8F92` (`parent_category_id`),
  KEY `IDX_5ED2C2B61220EA6` (`creator_id`),
  CONSTRAINT `FK_5ED2C2B61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`),
  CONSTRAINT `FK_5ED2C2B796A8F92` FOREIGN KEY (`parent_category_id`) REFERENCES `dtb_category` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=163 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_tag`（商品タグ）
```sql
CREATE TABLE `dtb_tag` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `sort_no` smallint(5) unsigned NOT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `mtb_product_status`（商品公開ステータス）
```sql
CREATE TABLE `mtb_product_status` (
  `id` smallint(5) unsigned NOT NULL,
  `name` varchar(255) NOT NULL,
  `sort_no` smallint(5) unsigned NOT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `mtb_sale_type`（販売種別）
```sql
CREATE TABLE `mtb_sale_type` (
  `id` smallint(5) unsigned NOT NULL,
  `name` varchar(255) NOT NULL,
  `sort_no` smallint(5) unsigned NOT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

---

## 3. 商品関連プラグイン・拡張テーブル

### `plg_related_product`（関連商品）
```sql
CREATE TABLE `plg_related_product` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `child_product_id` int(10) unsigned DEFAULT NULL,
  `content` varchar(4000) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_77B090F74584665A` (`product_id`),
  KEY `IDX_77B090F7A15B9831` (`child_product_id`),
  CONSTRAINT `FK_77B090F74584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_77B090F7A15B9831` FOREIGN KEY (`child_product_id`) REFERENCES `dtb_product` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=623 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `plg_recommend_product`（おすすめ商品）
```sql
CREATE TABLE `plg_recommend_product` (
  `recommend_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `comment` longtext DEFAULT NULL,
  `sort_no` int(11) DEFAULT NULL,
  `visible` tinyint(1) NOT NULL DEFAULT 1,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`recommend_id`),
  KEY `IDX_7EA2C2D14584665A` (`product_id`),
  CONSTRAINT `FK_7EA2C2D14584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `plg_productoption_dtb_product_option`（商品オプション紐付け）
```sql
CREATE TABLE `plg_productoption_dtb_product_option` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int(10) unsigned DEFAULT NULL,
  `option_id` int(10) unsigned DEFAULT NULL,
  `sort_no` int(11) NOT NULL,
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_839CC9504584665A` (`product_id`),
  KEY `IDX_839CC950A7C41D6F` (`option_id`),
  CONSTRAINT `FK_839CC9504584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_839CC950A7C41D6F` FOREIGN KEY (`option_id`) REFERENCES `plg_productoption_dtb_option` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=87 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `plg_productoption_dtb_option`（オプション項目定義）
```sql
CREATE TABLE `plg_productoption_dtb_option` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `backend_name` varchar(255) NOT NULL,
  `description` varchar(4000) DEFAULT NULL,
  `type` smallint(5) unsigned NOT NULL,
  `pricedisp_flg` tinyint(1) DEFAULT NULL,
  `description_flg` tinyint(1) DEFAULT NULL,
  `is_required` tinyint(1) DEFAULT NULL,
  `require_min` int(11) DEFAULT NULL,
  `require_max` int(11) DEFAULT NULL,
  `sort_no` int(11) NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_BCF07FE361220EA6` (`creator_id`),
  CONSTRAINT `FK_BCF07FE361220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `plg_productoption_dtb_optioncategory`（オプション選択肢）
```sql
CREATE TABLE `plg_productoption_dtb_optioncategory` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `option_id` int(10) unsigned DEFAULT NULL,
  `creator_id` int(10) unsigned DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `description` varchar(4000) DEFAULT NULL,
  `disable_flg` tinyint(1) DEFAULT NULL,
  `init_flg` tinyint(1) DEFAULT NULL,
  `hidden_flg` tinyint(1) DEFAULT NULL,
  `value` decimal(12,2) DEFAULT NULL,
  `delivery_free_flg` smallint(6) DEFAULT NULL,
  `multiple_flg` smallint(6) DEFAULT NULL,
  `weight` decimal(12,2) DEFAULT NULL,
  `size` decimal(12,2) DEFAULT NULL,
  `sort_no` int(11) NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_D196678DA7C41D6F` (`option_id`),
  KEY `IDX_D196678D61220EA6` (`creator_id`),
  CONSTRAINT `FK_D196678D61220EA6` FOREIGN KEY (`creator_id`) REFERENCES `dtb_member` (`id`),
  CONSTRAINT `FK_D196678DA7C41D6F` FOREIGN KEY (`option_id`) REFERENCES `plg_productoption_dtb_option` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=83 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `dtb_customer_favorite_product`（お気に入り商品）
```sql
CREATE TABLE `dtb_customer_favorite_product` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `customer_id` int(10) unsigned DEFAULT NULL,
  `product_id` int(10) unsigned DEFAULT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `discriminator_type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_ED6313839395C3F3` (`customer_id`),
  KEY `IDX_ED6313834584665A` (`product_id`),
  CONSTRAINT `FK_ED6313834584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_ED6313839395C3F3` FOREIGN KEY (`customer_id`) REFERENCES `dtb_customer` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=178 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

### `plg_product_review`（商品レビュー）
```sql
CREATE TABLE `plg_product_review` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `sex_id` smallint(5) unsigned DEFAULT NULL,
  `product_id` int(10) unsigned DEFAULT NULL,
  `customer_id` int(10) unsigned DEFAULT NULL,
  `status_id` smallint(5) unsigned DEFAULT NULL,
  `reviewer_name` varchar(255) NOT NULL,
  `reviewer_url` longtext DEFAULT NULL,
  `title` varchar(50) NOT NULL,
  `comment` longtext NOT NULL,
  `recommend_level` smallint(6) NOT NULL,
  `create_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  `update_date` datetime NOT NULL COMMENT '(DC2Type:datetimetz)',
  PRIMARY KEY (`id`),
  KEY `IDX_9CA38FA25A2DB2A0` (`sex_id`),
  KEY `IDX_9CA38FA24584665A` (`product_id`),
  KEY `IDX_9CA38FA29395C3F3` (`customer_id`),
  KEY `IDX_9CA38FA26BF700BD` (`status_id`),
  CONSTRAINT `FK_9CA38FA24584665A` FOREIGN KEY (`product_id`) REFERENCES `dtb_product` (`id`),
  CONSTRAINT `FK_9CA38FA25A2DB2A0` FOREIGN KEY (`sex_id`) REFERENCES `mtb_sex` (`id`),
  CONSTRAINT `FK_9CA38FA26BF700BD` FOREIGN KEY (`status_id`) REFERENCES `plg_product_review_status` (`id`),
  CONSTRAINT `FK_9CA38FA29395C3F3` FOREIGN KEY (`customer_id`) REFERENCES `dtb_customer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
```

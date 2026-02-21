# Modèle de données - Data Warehouse

## 1. Vue d'ensemble

Le Data Warehouse utilise un **schéma en étoile** (star schema) avec 3 schémas PostgreSQL :

| Schéma | Rôle | Tables |
|---|---|---|
| `staging_raw` | Zone d'atterrissage brute (miroir API) | 6 tables `*_raw` |
| `staging_clean` | Données normalisées et dédupliquées | 6 tables `*_clean` |
| `dwh` | Modèle dimensionnel (étoile) | 7 dimensions + 3 faits |

## 2. Staging Raw (miroir API)

Tables brutes alimentées par l'extraction API. Aucune contrainte de clé primaire,
les données sont insérées telles quelles depuis les endpoints ERP.

| Table | Source API | Colonnes principales |
|---|---|---|
| `customers_raw` | `GET /api/v1/customers` | customer_id, customer_name, segment, city, state, region, email |
| `suppliers_raw` | `GET /api/v1/suppliers` | supplier_id, supplier_name, country, contact_email, rating, lead_time_days |
| `products_raw` | `GET /api/v1/catalog/products` | product_id, product_name, category, sub_category, unit_cost, unit_price, supplier_id, stock_quantity |
| `orders_raw` | `GET /api/v1/sales/orders` | order_id, customer_id, order_date, ship_date, current_status, ship_mode, country, city, state, region |
| `order_lines_raw` | `GET /api/v1/sales/orders/:id` (lines) | row_id, order_id, product_id, quantity, discount, sales, unit_price, cost, profit |
| `order_status_history_raw` | `GET /api/v1/sales/orders/:id` (status_history) | id, order_id, status, status_date, updated_by |

Chaque table raw porte : `etl_loaded_at`, `etl_run_id`.

## 3. Staging Clean (normalisé)

Tables nettoyées avec clés primaires et colonnes normalisées.

| Table | PK | Transformations appliquées |
|---|---|---|
| `customers_clean` | `customer_id` | `trim(lower(name))`, `trim(lower(email))`, DISTINCT ON updated_at DESC |
| `suppliers_clean` | `supplier_id` | `trim(lower(name))`, `trim(lower(email))`, DISTINCT ON updated_at DESC |
| `products_clean` | `product_id` | `trim(lower(name))`, DISTINCT ON updated_at DESC |
| `orders_clean` | `order_id` | DISTINCT ON updated_at DESC, suppression ship_date < order_date |
| `order_lines_clean` | `row_id` | DISTINCT ON updated_at DESC |
| `order_status_history_clean` | `id` | DISTINCT ON created_at DESC |

## 4. Dimensions DWH

### dim_date
Dimension temporelle (grain = jour), générée automatiquement.

| Colonne | Type | Description |
|---|---|---|
| `date_key` (PK) | INTEGER | Format YYYYMMDD |
| `full_date` | DATE | Date complète |
| `day_of_month` | INTEGER | Jour du mois |
| `month_number` | INTEGER | Numéro du mois |
| `month_name` | TEXT | Nom abrégé (Jan, Feb...) |
| `quarter_number` | INTEGER | Trimestre (1-4) |
| `year_number` | INTEGER | Année |
| `is_weekend` | BOOLEAN | Samedi/dimanche |

### dim_geography
Dimension géographique déduite des commandes.

| Colonne | Type | Description |
|---|---|---|
| `geography_key` (PK) | BIGSERIAL | Surrogate key |
| `country` | TEXT | Pays |
| `region` | TEXT | Région |
| `state` | TEXT | État/département |
| `city` | TEXT | Ville |
| `postal_code` | TEXT | Code postal |
| `geography_hash` (UNIQUE) | TEXT | MD5 pour déduplication |

### dim_customer (SCD2-ready)

| Colonne | Type | Description |
|---|---|---|
| `customer_key` (PK) | BIGSERIAL | Surrogate key |
| `customer_id` | TEXT | Business key (OLTP) |
| `customer_name` | TEXT | Nom |
| `segment` | TEXT | Segment client |
| `city`, `state`, `region` | TEXT | Localisation |
| `email` | TEXT | Email |
| `valid_from` | TIMESTAMP | Début de validité |
| `valid_to` | TIMESTAMP | Fin de validité (NULL = courant) |
| `is_current` | BOOLEAN | Version active |
| `customer_hash` | TEXT | MD5 pour détection de changements |

### dim_supplier (SCD2-ready)

| Colonne | Type | Description |
|---|---|---|
| `supplier_key` (PK) | BIGSERIAL | Surrogate key |
| `supplier_id` | TEXT | Business key |
| `supplier_name` | TEXT | Nom |
| `country` | TEXT | Pays |
| `contact_email` | TEXT | Email contact |
| `rating` | NUMERIC(4,2) | Note (0-5) |
| `lead_time_days` | INTEGER | Délai approvisionnement |
| `active` | BOOLEAN | Fournisseur actif |
| `valid_from`, `valid_to`, `is_current`, `supplier_hash` | — | SCD2 |

### dim_product (SCD2-ready)

| Colonne | Type | Description |
|---|---|---|
| `product_key` (PK) | BIGSERIAL | Surrogate key |
| `product_id` | TEXT | Business key |
| `product_name` | TEXT | Nom |
| `category`, `sub_category` | TEXT | Classification |
| `unit_cost` | NUMERIC(14,4) | Coût unitaire |
| `unit_price` | NUMERIC(14,4) | Prix unitaire |
| `supplier_id` | TEXT | Fournisseur |
| `valid_from`, `valid_to`, `is_current`, `product_hash` | — | SCD2 |

### dim_order_status

| Colonne | Type | Description |
|---|---|---|
| `status_key` (PK) | BIGSERIAL | Surrogate key |
| `status_code` (UNIQUE) | TEXT | Code statut (Draft, Confirmed, Shipped...) |

### dim_ship_mode

| Colonne | Type | Description |
|---|---|---|
| `ship_mode_key` (PK) | BIGSERIAL | Surrogate key |
| `ship_mode_code` (UNIQUE) | TEXT | Mode livraison |

## 5. Faits DWH

### fact_sales_order_line (grain : 1 ligne de commande)

| Colonne | Type | Description |
|---|---|---|
| `fact_sales_order_line_key` (PK) | BIGSERIAL | Surrogate key |
| `order_id` | TEXT | ID commande (degenerate) |
| `row_id` | INTEGER | ID ligne (degenerate) |
| `order_date_key` → `dim_date` | INTEGER | Date commande |
| `ship_date_key` → `dim_date` | INTEGER | Date expédition |
| `customer_key` → `dim_customer` | BIGINT | Client |
| `product_key` → `dim_product` | BIGINT | Produit |
| `supplier_key` → `dim_supplier` | BIGINT | Fournisseur |
| `geography_key` → `dim_geography` | BIGINT | Localisation |
| `status_key` → `dim_order_status` | BIGINT | Statut |
| `ship_mode_key` → `dim_ship_mode` | BIGINT | Mode livraison |
| `quantity` | INTEGER | Quantité |
| `discount_rate` | NUMERIC(8,4) | Taux remise |
| `sales_amount` | NUMERIC(14,4) | Montant vente |
| `unit_price_amount` | NUMERIC(14,4) | Prix unitaire |
| `cost_amount` | NUMERIC(14,4) | Coût |
| `profit_amount` | NUMERIC(14,4) | Profit |
| UNIQUE | | `(order_id, row_id)` |

### fact_order_status_transition (grain : 1 changement de statut)

| Colonne | Type | Description |
|---|---|---|
| `fact_order_status_transition_key` (PK) | BIGSERIAL | Surrogate key |
| `order_id` | TEXT | ID commande |
| `status_date_key` → `dim_date` | INTEGER | Date du changement |
| `status_key` → `dim_order_status` | BIGINT | Nouveau statut |
| `customer_key` → `dim_customer` | BIGINT | Client |
| `transition_count` | INTEGER | Compteur (1) |
| `updated_by` | TEXT | Auteur |
| `status_date` | TIMESTAMP | Date/heure précise |
| UNIQUE | | `(order_id, status_key, status_date)` |

### fact_inventory_snapshot (grain : 1 produit par jour)

| Colonne | Type | Description |
|---|---|---|
| `fact_inventory_snapshot_key` (PK) | BIGSERIAL | Surrogate key |
| `snapshot_date_key` → `dim_date` | INTEGER | Date du snapshot |
| `product_key` → `dim_product` | BIGINT | Produit |
| `supplier_key` → `dim_supplier` | BIGINT | Fournisseur |
| `quantity_on_hand` | INTEGER | Stock disponible |
| `stock_value` | NUMERIC(18,4) | Valeur stock (qty × unit_cost) |
| UNIQUE | | `(snapshot_date_key, product_key)` |

## 6. Index de performance

| Index | Table | Colonnes |
|---|---|---|
| `idx_dim_customer_bk_current` | `dim_customer` | `(customer_id, is_current)` |
| `idx_dim_product_bk_current` | `dim_product` | `(product_id, is_current)` |
| `idx_dim_supplier_bk_current` | `dim_supplier` | `(supplier_id, is_current)` |
| `idx_fact_sales_order_date` | `fact_sales_order_line` | `(order_date_key)` |
| `idx_fact_sales_customer` | `fact_sales_order_line` | `(customer_key)` |
| `idx_fact_sales_product` | `fact_sales_order_line` | `(product_key)` |
| `idx_fact_transition_status_date` | `fact_order_status_transition` | `(status_date_key)` |
| `idx_fact_inventory_snapshot` | `fact_inventory_snapshot` | `(snapshot_date_key, product_key)` |

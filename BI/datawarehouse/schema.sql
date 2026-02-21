-- =============================================================================
-- Data Warehouse - Schema Etoile (Star Schema)
-- Base: erp_distribution_dwh
--
-- Structure:
--   1. Staging (raw + clean) : zone d'atterrissage ETL
--   2. DWH dimensions        : tables dimensionnelles (SCD2-ready)
--   3. DWH faits             : tables de faits (mesures)
--   4. Index                 : performance des jointures
-- =============================================================================

-- ===================== 1. STAGING =====================

CREATE SCHEMA IF NOT EXISTS staging_raw;
CREATE SCHEMA IF NOT EXISTS staging_clean;

-- Raw : miroir brut des donnees extraites de l'API ERP

CREATE TABLE IF NOT EXISTS staging_raw.customers_raw (
  customer_id TEXT,
  customer_name TEXT,
  segment TEXT,
  city TEXT,
  state TEXT,
  region TEXT,
  email TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_raw.suppliers_raw (
  supplier_id TEXT,
  supplier_name TEXT,
  country TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  rating NUMERIC(4,2),
  lead_time_days INTEGER,
  payment_terms TEXT,
  active BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_raw.products_raw (
  product_id TEXT,
  product_name TEXT,
  category TEXT,
  sub_category TEXT,
  unit_cost NUMERIC(14,4),
  unit_price NUMERIC(14,4),
  supplier_id TEXT,
  stock_quantity INTEGER,
  reorder_level INTEGER,
  reorder_quantity INTEGER,
  warehouse_location TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_raw.orders_raw (
  order_id TEXT,
  customer_id TEXT,
  order_date DATE,
  ship_date DATE,
  current_status TEXT,
  ship_mode TEXT,
  country TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  region TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_raw.order_lines_raw (
  row_id INTEGER,
  order_id TEXT,
  product_id TEXT,
  quantity INTEGER,
  discount NUMERIC(8,4),
  sales NUMERIC(14,4),
  unit_price NUMERIC(14,4),
  cost NUMERIC(14,4),
  profit NUMERIC(14,4),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_raw.order_status_history_raw (
  id BIGINT,
  order_id TEXT,
  status TEXT,
  status_date TIMESTAMP,
  updated_by TEXT,
  created_at TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT
);

-- Clean : donnees normalisees, deduplicees, pretes pour le DWH

CREATE TABLE IF NOT EXISTS staging_clean.customers_clean (
  customer_id TEXT PRIMARY KEY,
  customer_name TEXT,
  customer_name_normalized TEXT,
  segment TEXT,
  city TEXT,
  state TEXT,
  region TEXT,
  email TEXT,
  email_normalized TEXT,
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_clean.suppliers_clean (
  supplier_id TEXT PRIMARY KEY,
  supplier_name TEXT,
  supplier_name_normalized TEXT,
  country TEXT,
  contact_email TEXT,
  contact_email_normalized TEXT,
  rating NUMERIC(4,2),
  lead_time_days INTEGER,
  active BOOLEAN,
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_clean.products_clean (
  product_id TEXT PRIMARY KEY,
  product_name TEXT,
  product_name_normalized TEXT,
  category TEXT,
  sub_category TEXT,
  unit_cost NUMERIC(14,4),
  unit_price NUMERIC(14,4),
  supplier_id TEXT,
  stock_quantity INTEGER,
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_clean.orders_clean (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT,
  order_date DATE,
  ship_date DATE,
  current_status TEXT,
  ship_mode TEXT,
  country TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  region TEXT,
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_clean.order_lines_clean (
  row_id INTEGER PRIMARY KEY,
  order_id TEXT,
  product_id TEXT,
  quantity INTEGER,
  discount NUMERIC(8,4),
  sales NUMERIC(14,4),
  unit_price NUMERIC(14,4),
  cost NUMERIC(14,4),
  profit NUMERIC(14,4),
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

CREATE TABLE IF NOT EXISTS staging_clean.order_status_history_clean (
  id BIGINT PRIMARY KEY,
  order_id TEXT,
  status TEXT,
  status_date TIMESTAMP,
  updated_by TEXT,
  source_updated_at TIMESTAMP,
  etl_run_id TEXT
);

-- ===================== 2. DIMENSIONS (schema etoile) =====================

CREATE SCHEMA IF NOT EXISTS dwh;

-- dim_date : dimension temporelle (grain = jour)
CREATE TABLE IF NOT EXISTS dwh.dim_date (
  date_key INTEGER PRIMARY KEY,          -- YYYYMMDD
  full_date DATE NOT NULL UNIQUE,
  day_of_month INTEGER NOT NULL,
  month_number INTEGER NOT NULL,
  month_name TEXT NOT NULL,
  quarter_number INTEGER NOT NULL,
  year_number INTEGER NOT NULL,
  is_weekend BOOLEAN NOT NULL
);

-- dim_geography : dimension geographique (hash pour unicite)
CREATE TABLE IF NOT EXISTS dwh.dim_geography (
  geography_key BIGSERIAL PRIMARY KEY,
  country TEXT,
  region TEXT,
  state TEXT,
  city TEXT,
  postal_code TEXT,
  geography_hash TEXT UNIQUE
);

-- dim_customer : SCD2-ready (valid_from/valid_to/is_current)
CREATE TABLE IF NOT EXISTS dwh.dim_customer (
  customer_key BIGSERIAL PRIMARY KEY,
  customer_id TEXT NOT NULL,
  customer_name TEXT,
  segment TEXT,
  city TEXT,
  state TEXT,
  region TEXT,
  email TEXT,
  valid_from TIMESTAMP NOT NULL,
  valid_to TIMESTAMP,
  is_current BOOLEAN NOT NULL DEFAULT TRUE,
  customer_hash TEXT NOT NULL,
  UNIQUE (customer_id, valid_from)
);

-- dim_supplier : SCD2-ready
CREATE TABLE IF NOT EXISTS dwh.dim_supplier (
  supplier_key BIGSERIAL PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  supplier_name TEXT,
  country TEXT,
  contact_email TEXT,
  rating NUMERIC(4,2),
  lead_time_days INTEGER,
  active BOOLEAN,
  valid_from TIMESTAMP NOT NULL,
  valid_to TIMESTAMP,
  is_current BOOLEAN NOT NULL DEFAULT TRUE,
  supplier_hash TEXT NOT NULL,
  UNIQUE (supplier_id, valid_from)
);

-- dim_product : SCD2-ready
CREATE TABLE IF NOT EXISTS dwh.dim_product (
  product_key BIGSERIAL PRIMARY KEY,
  product_id TEXT NOT NULL,
  product_name TEXT,
  category TEXT,
  sub_category TEXT,
  unit_cost NUMERIC(14,4),
  unit_price NUMERIC(14,4),
  supplier_id TEXT,
  valid_from TIMESTAMP NOT NULL,
  valid_to TIMESTAMP,
  is_current BOOLEAN NOT NULL DEFAULT TRUE,
  product_hash TEXT NOT NULL,
  UNIQUE (product_id, valid_from)
);

-- dim_order_status : statuts de commande
CREATE TABLE IF NOT EXISTS dwh.dim_order_status (
  status_key BIGSERIAL PRIMARY KEY,
  status_code TEXT NOT NULL UNIQUE
);

-- dim_ship_mode : modes de livraison
CREATE TABLE IF NOT EXISTS dwh.dim_ship_mode (
  ship_mode_key BIGSERIAL PRIMARY KEY,
  ship_mode_code TEXT NOT NULL UNIQUE
);

-- ===================== 3. FAITS =====================

-- fact_sales_order_line : grain = une ligne de commande
CREATE TABLE IF NOT EXISTS dwh.fact_sales_order_line (
  fact_sales_order_line_key BIGSERIAL PRIMARY KEY,
  order_id TEXT NOT NULL,
  row_id INTEGER NOT NULL,
  order_date_key INTEGER REFERENCES dwh.dim_date(date_key),
  ship_date_key INTEGER REFERENCES dwh.dim_date(date_key),
  customer_key BIGINT REFERENCES dwh.dim_customer(customer_key),
  product_key BIGINT REFERENCES dwh.dim_product(product_key),
  supplier_key BIGINT REFERENCES dwh.dim_supplier(supplier_key),
  geography_key BIGINT REFERENCES dwh.dim_geography(geography_key),
  status_key BIGINT REFERENCES dwh.dim_order_status(status_key),
  ship_mode_key BIGINT REFERENCES dwh.dim_ship_mode(ship_mode_key),
  quantity INTEGER,
  discount_rate NUMERIC(8,4),
  sales_amount NUMERIC(14,4),
  unit_price_amount NUMERIC(14,4),
  cost_amount NUMERIC(14,4),
  profit_amount NUMERIC(14,4),
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT,
  UNIQUE (order_id, row_id)
);

-- fact_order_status_transition : grain = un changement de statut
CREATE TABLE IF NOT EXISTS dwh.fact_order_status_transition (
  fact_order_status_transition_key BIGSERIAL PRIMARY KEY,
  order_id TEXT NOT NULL,
  status_date_key INTEGER REFERENCES dwh.dim_date(date_key),
  status_key BIGINT REFERENCES dwh.dim_order_status(status_key),
  customer_key BIGINT REFERENCES dwh.dim_customer(customer_key),
  transition_count INTEGER NOT NULL DEFAULT 1,
  updated_by TEXT,
  status_date TIMESTAMP,
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT,
  UNIQUE (order_id, status_key, status_date)
);

-- fact_inventory_snapshot : grain = stock produit a une date
CREATE TABLE IF NOT EXISTS dwh.fact_inventory_snapshot (
  fact_inventory_snapshot_key BIGSERIAL PRIMARY KEY,
  snapshot_date_key INTEGER REFERENCES dwh.dim_date(date_key),
  product_key BIGINT REFERENCES dwh.dim_product(product_key),
  supplier_key BIGINT REFERENCES dwh.dim_supplier(supplier_key),
  quantity_on_hand INTEGER,
  stock_value NUMERIC(18,4),
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT,
  UNIQUE (snapshot_date_key, product_key)
);

-- ===================== 4. INDEX =====================

CREATE INDEX IF NOT EXISTS idx_dim_customer_bk_current
  ON dwh.dim_customer(customer_id, is_current);

CREATE INDEX IF NOT EXISTS idx_dim_product_bk_current
  ON dwh.dim_product(product_id, is_current);

CREATE INDEX IF NOT EXISTS idx_dim_supplier_bk_current
  ON dwh.dim_supplier(supplier_id, is_current);

CREATE INDEX IF NOT EXISTS idx_fact_sales_order_date
  ON dwh.fact_sales_order_line(order_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer
  ON dwh.fact_sales_order_line(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_product
  ON dwh.fact_sales_order_line(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_transition_status_date
  ON dwh.fact_order_status_transition(status_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_inventory_snapshot
  ON dwh.fact_inventory_snapshot(snapshot_date_key, product_key);

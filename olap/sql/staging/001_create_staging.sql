CREATE SCHEMA IF NOT EXISTS staging_raw;
CREATE SCHEMA IF NOT EXISTS staging_clean;

-- Raw tables mirror source with minimal typing constraints.
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

-- Clean layer with normalized technical columns.
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

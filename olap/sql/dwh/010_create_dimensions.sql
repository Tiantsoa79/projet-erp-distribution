CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS dwh.dim_date (
  date_key INTEGER PRIMARY KEY,
  full_date DATE NOT NULL UNIQUE,
  day_of_month INTEGER NOT NULL,
  month_number INTEGER NOT NULL,
  month_name TEXT NOT NULL,
  quarter_number INTEGER NOT NULL,
  year_number INTEGER NOT NULL,
  is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dwh.dim_geography (
  geography_key BIGSERIAL PRIMARY KEY,
  country TEXT,
  region TEXT,
  state TEXT,
  city TEXT,
  postal_code TEXT,
  geography_hash TEXT UNIQUE
);

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

CREATE TABLE IF NOT EXISTS dwh.dim_order_status (
  status_key BIGSERIAL PRIMARY KEY,
  status_code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dwh.dim_ship_mode (
  ship_mode_key BIGSERIAL PRIMARY KEY,
  ship_mode_code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dwh.dim_user (
  user_key BIGSERIAL PRIMARY KEY,
  user_id TEXT,
  username TEXT,
  full_name TEXT,
  is_active BOOLEAN,
  valid_from TIMESTAMP NOT NULL,
  valid_to TIMESTAMP,
  is_current BOOLEAN NOT NULL DEFAULT TRUE,
  user_hash TEXT,
  UNIQUE (user_id, valid_from)
);

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

CREATE TABLE IF NOT EXISTS dwh.fact_inventory_snapshot (
  fact_inventory_snapshot_key BIGSERIAL PRIMARY KEY,
  snapshot_date_key INTEGER REFERENCES dwh.dim_date(date_key),
  product_key BIGINT REFERENCES dwh.dim_product(product_key),
  supplier_key BIGINT REFERENCES dwh.dim_supplier(supplier_key),
  stock_quantity INTEGER,
  stock_value NUMERIC(18,4),
  etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
  etl_run_id TEXT,
  UNIQUE (snapshot_date_key, product_key)
);

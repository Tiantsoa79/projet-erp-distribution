CREATE TABLE IF NOT EXISTS customers (
  customer_id VARCHAR(32) PRIMARY KEY,
  customer_name TEXT NOT NULL,
  segment TEXT,
  city TEXT,
  state TEXT,
  region TEXT,
  gender VARCHAR(16),
  age INTEGER,
  email TEXT,
  registration_date DATE,
  total_sales NUMERIC(14, 2),
  total_profit NUMERIC(14, 2),
  total_orders INTEGER,
  average_order_value NUMERIC(14, 2),
  customer_segment_score TEXT,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id VARCHAR(32) PRIMARY KEY,
  supplier_name TEXT NOT NULL,
  country TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  rating NUMERIC(4, 2),
  lead_time_days INTEGER,
  payment_terms TEXT,
  active BOOLEAN,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  product_id VARCHAR(64) PRIMARY KEY,
  product_name TEXT NOT NULL,
  category TEXT,
  sub_category TEXT,
  unit_cost NUMERIC(14, 4),
  unit_price NUMERIC(14, 4),
  supplier_id VARCHAR(32) REFERENCES suppliers(supplier_id),
  total_units_sold INTEGER,
  margin_percentage NUMERIC(8, 4),
  stock_quantity INTEGER,
  reorder_level INTEGER,
  reorder_quantity INTEGER,
  warehouse_location TEXT,
  last_restock_date DATE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
  order_id VARCHAR(32) PRIMARY KEY,
  customer_id VARCHAR(32) REFERENCES customers(customer_id),
  order_date DATE,
  ship_date DATE,
  ship_mode TEXT,
  country TEXT,
  city TEXT,
  state TEXT,
  postal_code VARCHAR(16),
  region TEXT,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_lines (
  row_id INTEGER PRIMARY KEY,
  order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  product_id VARCHAR(64) REFERENCES products(product_id),
  quantity INTEGER,
  discount NUMERIC(8, 4),
  sales NUMERIC(14, 4),
  unit_price NUMERIC(14, 4),
  cost NUMERIC(14, 4),
  profit NUMERIC(14, 4),
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_status_history (
  id BIGSERIAL PRIMARY KEY,
  order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  status_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  updated_by TEXT,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE(order_id, status, status_date)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON order_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id);

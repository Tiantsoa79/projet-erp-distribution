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
  current_status TEXT NOT NULL DEFAULT 'Draft',
  ship_mode TEXT,
  country TEXT,
  city TEXT,
  state TEXT,
  postal_code VARCHAR(16),
  region TEXT,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS current_status TEXT NOT NULL DEFAULT 'Draft';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'orders_ship_date_after_order_date_check'
  ) THEN
    ALTER TABLE orders
      ADD CONSTRAINT orders_ship_date_after_order_date_check
      CHECK (ship_date IS NULL OR order_date IS NULL OR ship_date >= order_date);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'suppliers_rating_range_check'
  ) THEN
    ALTER TABLE suppliers
      ADD CONSTRAINT suppliers_rating_range_check
      CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'suppliers_lead_time_non_negative_check'
  ) THEN
    ALTER TABLE suppliers
      ADD CONSTRAINT suppliers_lead_time_non_negative_check
      CHECK (lead_time_days IS NULL OR lead_time_days >= 0);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'products_non_negative_values_check'
  ) THEN
    ALTER TABLE products
      ADD CONSTRAINT products_non_negative_values_check
      CHECK (
        (unit_cost IS NULL OR unit_cost >= 0)
        AND (unit_price IS NULL OR unit_price >= 0)
        AND (stock_quantity IS NULL OR stock_quantity >= 0)
        AND (reorder_level IS NULL OR reorder_level >= 0)
        AND (reorder_quantity IS NULL OR reorder_quantity >= 0)
      );
  END IF;

END $$;

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

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'order_lines_business_values_check'
  ) THEN
    ALTER TABLE order_lines DROP CONSTRAINT order_lines_business_values_check;
  END IF;

  ALTER TABLE order_lines
    ADD CONSTRAINT order_lines_business_values_check
    CHECK (
      (quantity IS NULL OR quantity > 0)
      AND (discount IS NULL OR (discount >= 0 AND discount <= 1))
      AND (sales IS NULL OR sales >= 0)
      AND (unit_price IS NULL OR unit_price >= 0)
      AND (cost IS NULL OR cost >= 0)
    );
END $$;

CREATE TABLE IF NOT EXISTS order_status_history (
  id BIGSERIAL PRIMARY KEY,
  order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  status_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  updated_by TEXT,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE(order_id, status, status_date)
);

CREATE TABLE IF NOT EXISTS users (
  user_id BIGSERIAL PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  token_version INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roles (
  role_id BIGSERIAL PRIMARY KEY,
  role_code VARCHAR(64) NOT NULL UNIQUE,
  role_name TEXT NOT NULL,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
  permission_id BIGSERIAL PRIMARY KEY,
  permission_code VARCHAR(128) NOT NULL UNIQUE,
  permission_name TEXT NOT NULL,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_users_token_version ON users(user_id, token_version);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
  permission_id BIGINT NOT NULL REFERENCES permissions(permission_id) ON DELETE CASCADE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGSERIAL PRIMARY KEY,
  entity_type VARCHAR(64) NOT NULL,
  entity_id VARCHAR(128) NOT NULL,
  action VARCHAR(64) NOT NULL,
  before_state JSONB,
  after_state JSONB,
  actor_user_id BIGINT,
  actor_username VARCHAR(128),
  request_id VARCHAR(128),
  source_service VARCHAR(64),
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounting_periods (
  period_id BIGSERIAL PRIMARY KEY,
  period_code VARCHAR(32) NOT NULL UNIQUE,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'open',
  closed_at TIMESTAMP WITHOUT TIME ZONE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  CHECK (start_date <= end_date),
  CHECK (status IN ('open', 'closed'))
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON order_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_orders_current_status ON orders(current_status);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_dates ON accounting_periods(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_username, actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request_id ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

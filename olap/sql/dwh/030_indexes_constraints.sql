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

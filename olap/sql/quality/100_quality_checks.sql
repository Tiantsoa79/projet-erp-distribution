-- 1) Nulls critiques sur les faits.
SELECT 'null_order_id_in_fact_sales' AS check_name, COUNT(*) AS anomaly_count
FROM dwh.fact_sales_order_line
WHERE order_id IS NULL;

SELECT 'null_product_key_in_fact_sales' AS check_name, COUNT(*) AS anomaly_count
FROM dwh.fact_sales_order_line
WHERE product_key IS NULL;

-- 2) Incoherences metier de base.
SELECT 'negative_sales_amount' AS check_name, COUNT(*) AS anomaly_count
FROM dwh.fact_sales_order_line
WHERE sales_amount < 0;

SELECT 'invalid_discount_rate' AS check_name, COUNT(*) AS anomaly_count
FROM dwh.fact_sales_order_line
WHERE discount_rate IS NOT NULL AND (discount_rate < 0 OR discount_rate > 1);

-- 3) FK orphelines logiques (si contraintes desactivees localement).
SELECT 'orphan_customer_key' AS check_name, COUNT(*) AS anomaly_count
FROM dwh.fact_sales_order_line f
LEFT JOIN dwh.dim_customer d ON f.customer_key = d.customer_key
WHERE f.customer_key IS NOT NULL AND d.customer_key IS NULL;

-- 4) Reconciliation simple volume.
SELECT 'count_orders_clean' AS metric_name, COUNT(*)::BIGINT AS metric_value
FROM staging_clean.orders_clean;

SELECT 'count_fact_sales_rows' AS metric_name, COUNT(*)::BIGINT AS metric_value
FROM dwh.fact_sales_order_line;

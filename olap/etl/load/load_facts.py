import os

import psycopg2


def get_conn():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )


def main():
    run_id = os.getenv("ETL_RUN_ID", "manual")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dwh.fact_sales_order_line (
                    order_id, row_id, order_date_key, ship_date_key,
                    customer_key, product_key, supplier_key, geography_key,
                    status_key, ship_mode_key,
                    quantity, discount_rate, sales_amount,
                    unit_price_amount, cost_amount, profit_amount,
                    etl_run_id
                )
                SELECT
                    o.order_id,
                    l.row_id,
                    CAST(to_char(o.order_date, 'YYYYMMDD') AS INTEGER),
                    CASE WHEN o.ship_date IS NOT NULL THEN CAST(to_char(o.ship_date, 'YYYYMMDD') AS INTEGER) END,
                    dc.customer_key,
                    dp.product_key,
                    ds.supplier_key,
                    dg.geography_key,
                    st.status_key,
                    sm.ship_mode_key,
                    l.quantity,
                    l.discount,
                    l.sales,
                    l.unit_price,
                    l.cost,
                    l.profit,
                    %s
                FROM staging_clean.orders_clean o
                JOIN staging_clean.order_lines_clean l ON l.order_id = o.order_id
                LEFT JOIN dwh.dim_customer dc ON dc.customer_id = o.customer_id AND dc.is_current = TRUE
                LEFT JOIN dwh.dim_product dp ON dp.product_id = l.product_id AND dp.is_current = TRUE
                LEFT JOIN dwh.dim_supplier ds ON ds.supplier_id = dp.supplier_id AND ds.is_current = TRUE
                LEFT JOIN dwh.dim_geography dg
                  ON dg.geography_hash = md5(concat_ws('|', o.country, o.region, o.state, o.city, o.postal_code))
                LEFT JOIN dwh.dim_order_status st ON st.status_code = o.current_status
                LEFT JOIN dwh.dim_ship_mode sm ON sm.ship_mode_code = o.ship_mode
                ON CONFLICT (order_id, row_id) DO UPDATE SET
                    order_date_key = EXCLUDED.order_date_key,
                    ship_date_key = EXCLUDED.ship_date_key,
                    customer_key = EXCLUDED.customer_key,
                    product_key = EXCLUDED.product_key,
                    supplier_key = EXCLUDED.supplier_key,
                    geography_key = EXCLUDED.geography_key,
                    status_key = EXCLUDED.status_key,
                    ship_mode_key = EXCLUDED.ship_mode_key,
                    quantity = EXCLUDED.quantity,
                    discount_rate = EXCLUDED.discount_rate,
                    sales_amount = EXCLUDED.sales_amount,
                    unit_price_amount = EXCLUDED.unit_price_amount,
                    cost_amount = EXCLUDED.cost_amount,
                    profit_amount = EXCLUDED.profit_amount,
                    etl_run_id = EXCLUDED.etl_run_id,
                    etl_loaded_at = NOW();
                """,
                (run_id,),
            )

            cur.execute(
                """
                INSERT INTO dwh.fact_order_status_transition (
                    order_id, status_date_key, status_key, customer_key,
                    transition_count, updated_by, status_date, etl_run_id
                )
                SELECT
                    h.order_id,
                    CAST(to_char(h.status_date::date, 'YYYYMMDD') AS INTEGER),
                    st.status_key,
                    dc.customer_key,
                    1,
                    h.updated_by,
                    h.status_date,
                    %s
                FROM staging_clean.order_status_history_clean h
                LEFT JOIN staging_clean.orders_clean o ON o.order_id = h.order_id
                LEFT JOIN dwh.dim_order_status st ON st.status_code = h.status
                LEFT JOIN dwh.dim_customer dc ON dc.customer_id = o.customer_id AND dc.is_current = TRUE
                ON CONFLICT (order_id, status_key, status_date) DO UPDATE SET
                    customer_key = EXCLUDED.customer_key,
                    transition_count = EXCLUDED.transition_count,
                    updated_by = EXCLUDED.updated_by,
                    etl_run_id = EXCLUDED.etl_run_id,
                    etl_loaded_at = NOW();
                """,
                (run_id,),
            )

            cur.execute(
                """
                INSERT INTO dwh.fact_inventory_snapshot (
                    snapshot_date_key, product_key, supplier_key,
                    stock_quantity, stock_value, etl_run_id
                )
                SELECT
                    CAST(to_char(CURRENT_DATE, 'YYYYMMDD') AS INTEGER),
                    dp.product_key,
                    ds.supplier_key,
                    p.stock_quantity,
                    COALESCE(p.stock_quantity, 0) * COALESCE(p.unit_cost, 0),
                    %s
                FROM staging_clean.products_clean p
                LEFT JOIN dwh.dim_product dp ON dp.product_id = p.product_id AND dp.is_current = TRUE
                LEFT JOIN dwh.dim_supplier ds ON ds.supplier_id = p.supplier_id AND ds.is_current = TRUE
                ON CONFLICT (snapshot_date_key, product_key) DO UPDATE SET
                    supplier_key = EXCLUDED.supplier_key,
                    stock_quantity = EXCLUDED.stock_quantity,
                    stock_value = EXCLUDED.stock_value,
                    etl_run_id = EXCLUDED.etl_run_id,
                    etl_loaded_at = NOW();
                """,
                (run_id,),
            )

        conn.commit()
    finally:
        conn.close()

    print("Load facts completed")


if __name__ == "__main__":
    main()

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
            # Minimal Type-1 upsert seed before SCD2 hardening.
            cur.execute(
                """
                INSERT INTO dwh.dim_customer (
                  customer_id, customer_name, segment, city, state, region, email,
                  valid_from, valid_to, is_current, customer_hash
                )
                SELECT
                  c.customer_id, c.customer_name, c.segment, c.city, c.state, c.region, c.email,
                  NOW(), NULL, TRUE,
                  md5(concat_ws('|', c.customer_name, c.segment, c.city, c.state, c.region, c.email))
                FROM staging_clean.customers_clean c
                LEFT JOIN dwh.dim_customer d
                  ON d.customer_id = c.customer_id AND d.is_current = TRUE
                WHERE d.customer_id IS NULL;
                """
            )

            cur.execute(
                """
                INSERT INTO dwh.dim_supplier (
                  supplier_id, supplier_name, country, contact_email, rating, lead_time_days,
                  active, valid_from, valid_to, is_current, supplier_hash
                )
                SELECT
                  s.supplier_id, s.supplier_name, s.country, s.contact_email, s.rating, s.lead_time_days,
                  s.active, NOW(), NULL, TRUE,
                  md5(concat_ws('|', s.supplier_name, s.country, s.contact_email, s.rating, s.lead_time_days, s.active))
                FROM staging_clean.suppliers_clean s
                LEFT JOIN dwh.dim_supplier d
                  ON d.supplier_id = s.supplier_id AND d.is_current = TRUE
                WHERE d.supplier_id IS NULL;
                """
            )

            cur.execute(
                """
                INSERT INTO dwh.dim_product (
                  product_id, product_name, category, sub_category, unit_cost, unit_price,
                  supplier_id, valid_from, valid_to, is_current, product_hash
                )
                SELECT
                  p.product_id, p.product_name, p.category, p.sub_category, p.unit_cost, p.unit_price,
                  p.supplier_id, NOW(), NULL, TRUE,
                  md5(concat_ws('|', p.product_name, p.category, p.sub_category, p.unit_cost, p.unit_price, p.supplier_id))
                FROM staging_clean.products_clean p
                LEFT JOIN dwh.dim_product d
                  ON d.product_id = p.product_id AND d.is_current = TRUE
                WHERE d.product_id IS NULL;
                """
            )

            cur.execute(
                """
                INSERT INTO dwh.dim_order_status(status_code)
                SELECT DISTINCT current_status
                FROM staging_clean.orders_clean
                WHERE current_status IS NOT NULL
                ON CONFLICT (status_code) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO dwh.dim_ship_mode(ship_mode_code)
                SELECT DISTINCT ship_mode
                FROM staging_clean.orders_clean
                WHERE ship_mode IS NOT NULL
                ON CONFLICT (ship_mode_code) DO NOTHING;
                """
            )

        conn.commit()
    finally:
        conn.close()

    print(f"Conform dimensions completed (run_id={run_id})")


if __name__ == "__main__":
    main()

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
    conn = get_conn()
    issues = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT customer_name_normalized, COALESCE(email_normalized, ''), COUNT(*)
                FROM staging_clean.customers_clean
                GROUP BY customer_name_normalized, COALESCE(email_normalized, '')
                HAVING COUNT(*) > 1;
                """
            )
            issues["customer_duplicates"] = cur.rowcount

            cur.execute(
                """
                SELECT product_name_normalized, COALESCE(supplier_id, ''), COUNT(*)
                FROM staging_clean.products_clean
                GROUP BY product_name_normalized, COALESCE(supplier_id, '')
                HAVING COUNT(*) > 1;
                """
            )
            issues["product_duplicates"] = cur.rowcount

            cur.execute(
                """
                DELETE FROM staging_clean.orders_clean
                WHERE order_date IS NOT NULL AND ship_date IS NOT NULL AND ship_date < order_date;
                """
            )
            issues["invalid_order_dates_removed"] = cur.rowcount

        conn.commit()
    finally:
        conn.close()

    print("Deduplicate/quality pass completed", issues)


if __name__ == "__main__":
    main()

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


def test_no_negative_sales_amount():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM dwh.fact_sales_order_line WHERE sales_amount < 0")
            count = cur.fetchone()[0]
            assert count == 0, f"Negative sales rows found: {count}"
    finally:
        conn.close()


def test_no_invalid_discount():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM dwh.fact_sales_order_line
                WHERE discount_rate IS NOT NULL AND (discount_rate < 0 OR discount_rate > 1)
                """
            )
            count = cur.fetchone()[0]
            assert count == 0, f"Invalid discount rows found: {count}"
    finally:
        conn.close()

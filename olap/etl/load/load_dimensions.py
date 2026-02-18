import os

import psycopg2
from dotenv import load_dotenv


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
    try:
        with conn.cursor() as cur:
            # Populate date dimension from order dates available in clean staging.
            cur.execute(
                """
                INSERT INTO dwh.dim_date (
                    date_key, full_date, day_of_month, month_number, month_name, quarter_number, year_number, is_weekend
                )
                SELECT DISTINCT
                    CAST(to_char(d, 'YYYYMMDD') AS INTEGER) AS date_key,
                    d AS full_date,
                    EXTRACT(DAY FROM d)::INT,
                    EXTRACT(MONTH FROM d)::INT,
                    to_char(d, 'Mon'),
                    EXTRACT(QUARTER FROM d)::INT,
                    EXTRACT(YEAR FROM d)::INT,
                    EXTRACT(ISODOW FROM d) IN (6, 7)
                FROM (
                    SELECT order_date::date AS d FROM staging_clean.orders_clean WHERE order_date IS NOT NULL
                    UNION
                    SELECT ship_date::date AS d FROM staging_clean.orders_clean WHERE ship_date IS NOT NULL
                    UNION
                    SELECT status_date::date AS d FROM staging_clean.order_status_history_clean WHERE status_date IS NOT NULL
                    UNION
                    SELECT CURRENT_DATE AS d  -- Add current date for snapshot dates
                ) src
                ON CONFLICT (date_key) DO NOTHING;
                """
            )

            # Geography conformation from orders clean.
            cur.execute(
                """
                INSERT INTO dwh.dim_geography (country, region, state, city, postal_code, geography_hash)
                SELECT DISTINCT
                    country,
                    region,
                    state,
                    city,
                    postal_code,
                    md5(concat_ws('|', country, region, state, city, postal_code))
                FROM staging_clean.orders_clean
                ON CONFLICT (geography_hash) DO NOTHING;
                """
            )

        conn.commit()
    finally:
        conn.close()

    print("Load dimensions completed")


if __name__ == "__main__":
    load_dotenv("olap/configs/.env")
    main()

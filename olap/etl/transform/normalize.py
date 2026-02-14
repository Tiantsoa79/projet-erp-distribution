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
                TRUNCATE TABLE
                  staging_clean.customers_clean,
                  staging_clean.suppliers_clean,
                  staging_clean.products_clean,
                  staging_clean.orders_clean,
                  staging_clean.order_lines_clean,
                  staging_clean.order_status_history_clean;
                """
            )

            # Customers
            cur.execute(
                """
                INSERT INTO staging_clean.customers_clean (
                    customer_id, customer_name, customer_name_normalized,
                    segment, city, state, region,
                    email, email_normalized, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (customer_id)
                    customer_id,
                    customer_name,
                    lower(trim(customer_name)),
                    segment, city, state, region,
                    email,
                    lower(trim(email)),
                    updated_at,
                    %s
                FROM staging_raw.customers_raw
                WHERE customer_id IS NOT NULL
                ORDER BY customer_id, updated_at DESC
                """,
                (run_id,),
            )

            # Suppliers
            cur.execute(
                """
                INSERT INTO staging_clean.suppliers_clean (
                    supplier_id, supplier_name, supplier_name_normalized,
                    country, contact_email, contact_email_normalized,
                    rating, lead_time_days, active, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (supplier_id)
                    supplier_id,
                    supplier_name,
                    lower(trim(supplier_name)),
                    country,
                    contact_email,
                    lower(trim(contact_email)),
                    rating,
                    lead_time_days,
                    active,
                    updated_at,
                    %s
                FROM staging_raw.suppliers_raw
                WHERE supplier_id IS NOT NULL
                ORDER BY supplier_id, updated_at DESC NULLS LAST;
                """,
                (run_id,),
            )

            # Orders
            cur.execute(
                """
                INSERT INTO staging_clean.orders_clean (
                    order_id, customer_id, order_date, ship_date,
                    current_status, ship_mode, country, city, state,
                    postal_code, region, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (order_id)
                    order_id, customer_id, order_date, ship_date,
                    current_status, ship_mode, country, city, state,
                    postal_code, region, updated_at, %s
                FROM staging_raw.orders_raw
                WHERE order_id IS NOT NULL
                ORDER BY order_id, updated_at DESC
                """,
                (run_id,),
            )

            # Products
            cur.execute(
                """
                INSERT INTO staging_clean.products_clean (
                    product_id, product_name, product_name_normalized, category, sub_category,
                    unit_cost, unit_price, supplier_id, stock_quantity, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (product_id)
                    product_id,
                    product_name,
                    lower(trim(product_name)),
                    category,
                    sub_category,
                    unit_cost,
                    unit_price,
                    supplier_id,
                    stock_quantity,
                    updated_at,
                    %s
                FROM staging_raw.products_raw
                WHERE product_id IS NOT NULL
                ORDER BY product_id, updated_at DESC
                """,
                (run_id,),
            )

            # Order lines
            cur.execute(
                """
                INSERT INTO staging_clean.order_lines_clean (
                    row_id, order_id, product_id, quantity, discount, sales,
                    unit_price, cost, profit, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (row_id)
                    row_id,
                    order_id,
                    product_id,
                    quantity,
                    discount,
                    sales,
                    unit_price,
                    cost,
                    profit,
                    updated_at,
                    %s
                FROM staging_raw.order_lines_raw
                WHERE row_id IS NOT NULL
                ORDER BY row_id, updated_at DESC NULLS LAST;
                """,
                (run_id,),
            )

            # Order status history
            cur.execute(
                """
                INSERT INTO staging_clean.order_status_history_clean (
                    id, order_id, status, status_date, updated_by, source_updated_at, etl_run_id
                )
                SELECT DISTINCT ON (id)
                    id,
                    order_id,
                    status,
                    status_date,
                    updated_by,
                    created_at,
                    %s
                FROM staging_raw.order_status_history_raw
                WHERE id IS NOT NULL
                ORDER BY id, created_at DESC NULLS LAST;
                """,
                (run_id,),
            )

        conn.commit()
    finally:
        conn.close()

    print("Normalize completed")


if __name__ == "__main__":
    main()

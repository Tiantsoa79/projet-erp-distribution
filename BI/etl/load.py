"""
ETL - Load
===========
Chargement des donnees transformees (staging_clean) vers le Data Warehouse (dwh.*).

Deux phases :

1. DIMENSIONS
   - dim_date      : generee a partir de toutes les dates (commandes, expeditions,
                     transitions de statut, date courante pour les snapshots)
   - dim_geography : hash unique (pays|region|etat|ville|code_postal)

2. FAITS (upsert idempotent via ON CONFLICT)
   - fact_sales_order_line        : grain = ligne de commande
   - fact_order_status_transition : grain = changement de statut commande
   - fact_inventory_snapshot      : grain = stock produit a la date du jour
"""

import os

import psycopg2


def get_dwh_conn():
    return psycopg2.connect(
        host=os.getenv("DWH_PGHOST", "localhost"),
        port=int(os.getenv("DWH_PGPORT", "5432")),
        dbname=os.getenv("DWH_PGDATABASE"),
        user=os.getenv("DWH_PGUSER"),
        password=os.getenv("DWH_PGPASSWORD"),
    )


# ---------------------------------------------------------------------------
# Phase 1 : Dimensions (date + geography)
# ---------------------------------------------------------------------------

def load_dimensions(cur):
    # dim_date : toutes les dates presentes dans staging + date courante
    cur.execute("""
        INSERT INTO dwh.dim_date (
            date_key, full_date, day_of_month, month_number,
            month_name, quarter_number, year_number, is_weekend
        )
        SELECT DISTINCT
            CAST(to_char(d, 'YYYYMMDD') AS INTEGER),
            d,
            EXTRACT(DAY FROM d)::INT,
            EXTRACT(MONTH FROM d)::INT,
            to_char(d, 'Mon'),
            EXTRACT(QUARTER FROM d)::INT,
            EXTRACT(YEAR FROM d)::INT,
            EXTRACT(ISODOW FROM d) IN (6, 7)
        FROM (
            SELECT CURRENT_DATE::date AS d
            UNION
            SELECT order_date::date FROM staging_clean.orders_clean WHERE order_date IS NOT NULL
            UNION
            SELECT ship_date::date FROM staging_clean.orders_clean WHERE ship_date IS NOT NULL
            UNION
            SELECT status_date::date FROM staging_clean.order_status_history_clean WHERE status_date IS NOT NULL
        ) src
        ON CONFLICT (date_key) DO NOTHING
    """)

    # dim_geography
    cur.execute("""
        INSERT INTO dwh.dim_geography (country, region, state, city, postal_code, geography_hash)
        SELECT DISTINCT
            country, region, state, city, postal_code,
            md5(concat_ws('|', country, region, state, city, postal_code))
        FROM staging_clean.orders_clean
        ON CONFLICT (geography_hash) DO NOTHING
    """)


# ---------------------------------------------------------------------------
# Phase 2 : Faits
# ---------------------------------------------------------------------------

def load_facts(cur, run_id: str):

    # fact_sales_order_line
    cur.execute("""
        INSERT INTO dwh.fact_sales_order_line (
            order_id, row_id, order_date_key, ship_date_key,
            customer_key, product_key, supplier_key, geography_key,
            status_key, ship_mode_key,
            quantity, discount_rate, sales_amount,
            unit_price_amount, cost_amount, profit_amount, etl_run_id
        )
        SELECT
            o.order_id, l.row_id,
            CAST(to_char(o.order_date, 'YYYYMMDD') AS INTEGER),
            CASE WHEN o.ship_date IS NOT NULL
                 THEN CAST(to_char(o.ship_date, 'YYYYMMDD') AS INTEGER) END,
            dc.customer_key, dp.product_key, ds.supplier_key, dg.geography_key,
            st.status_key, sm.ship_mode_key,
            l.quantity, l.discount, l.sales,
            l.unit_price, l.cost, l.profit, %s
        FROM staging_clean.orders_clean o
        JOIN staging_clean.order_lines_clean l ON l.order_id = o.order_id
        LEFT JOIN dwh.dim_customer dc   ON dc.customer_id = o.customer_id AND dc.is_current = TRUE
        LEFT JOIN dwh.dim_product dp    ON dp.product_id = l.product_id AND dp.is_current = TRUE
        LEFT JOIN dwh.dim_supplier ds   ON ds.supplier_id = dp.supplier_id AND ds.is_current = TRUE
        LEFT JOIN dwh.dim_geography dg  ON dg.geography_hash = md5(concat_ws('|', o.country, o.region, o.state, o.city, o.postal_code))
        LEFT JOIN dwh.dim_order_status st ON st.status_code = o.current_status
        LEFT JOIN dwh.dim_ship_mode sm    ON sm.ship_mode_code = o.ship_mode
        ON CONFLICT (order_id, row_id) DO UPDATE SET
            order_date_key    = EXCLUDED.order_date_key,
            ship_date_key     = EXCLUDED.ship_date_key,
            customer_key      = EXCLUDED.customer_key,
            product_key       = EXCLUDED.product_key,
            supplier_key      = EXCLUDED.supplier_key,
            geography_key     = EXCLUDED.geography_key,
            status_key        = EXCLUDED.status_key,
            ship_mode_key     = EXCLUDED.ship_mode_key,
            quantity          = EXCLUDED.quantity,
            discount_rate     = EXCLUDED.discount_rate,
            sales_amount      = EXCLUDED.sales_amount,
            unit_price_amount = EXCLUDED.unit_price_amount,
            cost_amount       = EXCLUDED.cost_amount,
            profit_amount     = EXCLUDED.profit_amount,
            etl_run_id        = EXCLUDED.etl_run_id,
            etl_loaded_at     = NOW();
    """, (run_id,))

    # fact_order_status_transition
    cur.execute("""
        INSERT INTO dwh.fact_order_status_transition (
            order_id, status_date_key, status_key, customer_key,
            transition_count, updated_by, status_date, etl_run_id
        )
        SELECT
            h.order_id,
            CAST(to_char(h.status_date::date, 'YYYYMMDD') AS INTEGER),
            st.status_key, dc.customer_key,
            1, h.updated_by, h.status_date, %s
        FROM staging_clean.order_status_history_clean h
        LEFT JOIN staging_clean.orders_clean o  ON o.order_id = h.order_id
        LEFT JOIN dwh.dim_order_status st       ON st.status_code = h.status
        LEFT JOIN dwh.dim_customer dc           ON dc.customer_id = o.customer_id AND dc.is_current = TRUE
        ON CONFLICT (order_id, status_key, status_date) DO UPDATE SET
            customer_key     = EXCLUDED.customer_key,
            transition_count = EXCLUDED.transition_count,
            updated_by       = EXCLUDED.updated_by,
            etl_run_id       = EXCLUDED.etl_run_id,
            etl_loaded_at    = NOW();
    """, (run_id,))

    # fact_inventory_snapshot (photo quotidienne du stock)
    cur.execute("""
        INSERT INTO dwh.fact_inventory_snapshot (
            snapshot_date_key, product_key, supplier_key,
            quantity_on_hand, stock_value, etl_run_id
        )
        SELECT
            CAST(to_char(CURRENT_DATE, 'YYYYMMDD') AS INTEGER),
            dp.product_key, ds.supplier_key,
            p.stock_quantity,
            COALESCE(p.stock_quantity, 0) * COALESCE(p.unit_cost, 0),
            %s
        FROM staging_clean.products_clean p
        LEFT JOIN dwh.dim_product dp   ON dp.product_id = p.product_id AND dp.is_current = TRUE
        LEFT JOIN dwh.dim_supplier ds  ON ds.supplier_id = p.supplier_id AND ds.is_current = TRUE
        ON CONFLICT (snapshot_date_key, product_key) DO UPDATE SET
            supplier_key   = EXCLUDED.supplier_key,
            quantity_on_hand = EXCLUDED.quantity_on_hand,
            stock_value    = EXCLUDED.stock_value,
            etl_run_id     = EXCLUDED.etl_run_id,
            etl_loaded_at  = NOW();
    """, (run_id,))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(run_id: str):
    conn = get_dwh_conn()
    try:
        with conn.cursor() as cur:
            print("[load] Chargement dimensions (date, geography)...")
            load_dimensions(cur)

            print("[load] Chargement faits (sales, transitions, inventory)...")
            load_facts(cur, run_id)

        conn.commit()
    finally:
        conn.close()

    print("[load] Done")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    run(os.getenv("ETL_RUN_ID", "manual"))

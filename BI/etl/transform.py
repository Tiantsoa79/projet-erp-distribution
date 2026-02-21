"""
ETL - Transform
================
Transformation des donnees brutes (staging_raw) vers staging_clean.

Trois phases appliquees sequentiellement :

1. NORMALISATION
   - Suppression espaces superflus (trim)
   - Mise en minuscule des champs texte de comparaison (noms, emails)
   - Deduplication par cle naturelle (DISTINCT ON ... ORDER BY updated_at DESC)
   - Justification : assure la coherence inter-modules (clients, produits,
     fournisseurs provenant de services ERP differents) et prepare la
     conformite dimensionnelle.

2. DEDUPLICATION / QUALITE
   - Detection des doublons clients (meme nom normalise + email)
   - Detection des doublons produits (meme nom normalise + fournisseur)
   - Suppression des commandes incoherentes (ship_date < order_date)
   - Justification : gestion des doublons et incoherences comme requis
     par la gouvernance des donnees (Partie B).

3. CONFORMATION DIMENSIONNELLE
   - Insertion des nouvelles entites dans les dimensions DWH (Type-1 upsert)
   - Population des dimensions de reference (statuts, modes de livraison)
   - Justification : prepare le chargement des faits en garantissant que
     chaque cle etrangere dimensionnelle est resolue.
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
# Phase 1 : Normalisation  (staging_raw -> staging_clean)
# ---------------------------------------------------------------------------

def normalize(cur, run_id: str):
    """Full-refresh : truncate clean puis insertion normalisee."""

    cur.execute("""
        TRUNCATE TABLE
            staging_clean.customers_clean,
            staging_clean.suppliers_clean,
            staging_clean.products_clean,
            staging_clean.orders_clean,
            staging_clean.order_lines_clean,
            staging_clean.order_status_history_clean;
    """)

    # Customers : normalise nom + email, derniere version par customer_id
    cur.execute("""
        INSERT INTO staging_clean.customers_clean (
            customer_id, customer_name, customer_name_normalized,
            segment, city, state, region,
            email, email_normalized, source_updated_at, etl_run_id
        )
        SELECT DISTINCT ON (customer_id)
            customer_id, customer_name, lower(trim(customer_name)),
            segment, city, state, region,
            email, lower(trim(email)), updated_at, %s
        FROM staging_raw.customers_raw
        WHERE customer_id IS NOT NULL
        ORDER BY customer_id, updated_at DESC
    """, (run_id,))

    # Suppliers : normalise nom + email contact
    cur.execute("""
        INSERT INTO staging_clean.suppliers_clean (
            supplier_id, supplier_name, supplier_name_normalized,
            country, contact_email, contact_email_normalized,
            rating, lead_time_days, active, source_updated_at, etl_run_id
        )
        SELECT DISTINCT ON (supplier_id)
            supplier_id, supplier_name, lower(trim(supplier_name)),
            country, contact_email, lower(trim(contact_email)),
            rating, lead_time_days, active, updated_at, %s
        FROM staging_raw.suppliers_raw
        WHERE supplier_id IS NOT NULL
        ORDER BY supplier_id, updated_at DESC NULLS LAST
    """, (run_id,))

    # Orders : derniere version par order_id
    cur.execute("""
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
    """, (run_id,))

    # Products : normalise nom
    cur.execute("""
        INSERT INTO staging_clean.products_clean (
            product_id, product_name, product_name_normalized, category, sub_category,
            unit_cost, unit_price, supplier_id, stock_quantity, source_updated_at, etl_run_id
        )
        SELECT DISTINCT ON (product_id)
            product_id, product_name, lower(trim(product_name)),
            category, sub_category, unit_cost, unit_price,
            supplier_id, stock_quantity, updated_at, %s
        FROM staging_raw.products_raw
        WHERE product_id IS NOT NULL
        ORDER BY product_id, updated_at DESC
    """, (run_id,))

    # Order lines : derniere version par row_id
    cur.execute("""
        INSERT INTO staging_clean.order_lines_clean (
            row_id, order_id, product_id, quantity, discount, sales,
            unit_price, cost, profit, source_updated_at, etl_run_id
        )
        SELECT DISTINCT ON (row_id)
            row_id, order_id, product_id, quantity, discount, sales,
            unit_price, cost, profit, updated_at, %s
        FROM staging_raw.order_lines_raw
        WHERE row_id IS NOT NULL
        ORDER BY row_id, updated_at DESC NULLS LAST
    """, (run_id,))

    # Order status history : derniere version par id
    cur.execute("""
        INSERT INTO staging_clean.order_status_history_clean (
            id, order_id, status, status_date, updated_by, source_updated_at, etl_run_id
        )
        SELECT DISTINCT ON (id)
            id, order_id, status, status_date, updated_by, created_at, %s
        FROM staging_raw.order_status_history_raw
        WHERE id IS NOT NULL
        ORDER BY id, created_at DESC NULLS LAST
    """, (run_id,))


# ---------------------------------------------------------------------------
# Phase 2 : Deduplication et controles qualite
# ---------------------------------------------------------------------------

def deduplicate(cur):
    """Detecte les doublons et supprime les donnees incoherentes."""
    issues = {}

    # Doublons clients (meme nom normalise + email)
    cur.execute("""
        SELECT customer_name_normalized, COALESCE(email_normalized, ''), COUNT(*)
        FROM staging_clean.customers_clean
        GROUP BY customer_name_normalized, COALESCE(email_normalized, '')
        HAVING COUNT(*) > 1
    """)
    issues["customer_duplicates"] = cur.rowcount

    # Doublons produits (meme nom normalise + fournisseur)
    cur.execute("""
        SELECT product_name_normalized, COALESCE(supplier_id, ''), COUNT(*)
        FROM staging_clean.products_clean
        GROUP BY product_name_normalized, COALESCE(supplier_id, '')
        HAVING COUNT(*) > 1
    """)
    issues["product_duplicates"] = cur.rowcount

    # Commandes incoherentes : ship_date avant order_date
    cur.execute("""
        DELETE FROM staging_clean.orders_clean
        WHERE order_date IS NOT NULL AND ship_date IS NOT NULL AND ship_date < order_date
    """)
    issues["invalid_order_dates_removed"] = cur.rowcount

    return issues


# ---------------------------------------------------------------------------
# Phase 3 : Conformation dimensionnelle
# ---------------------------------------------------------------------------

def conform_dimensions(cur, run_id: str):
    """Insere les nouvelles entites dans les dimensions DWH."""

    # dim_customer (Type-1 insert pour nouvelles entrees)
    cur.execute("""
        INSERT INTO dwh.dim_customer (
            customer_id, customer_name, segment, city, state, region, email,
            valid_from, valid_to, is_current, customer_hash
        )
        SELECT
            c.customer_id, c.customer_name, c.segment, c.city, c.state, c.region, c.email,
            NOW(), NULL, TRUE,
            md5(concat_ws('|', c.customer_name, c.segment, c.city, c.state, c.region, c.email))
        FROM staging_clean.customers_clean c
        LEFT JOIN dwh.dim_customer d ON d.customer_id = c.customer_id AND d.is_current = TRUE
        WHERE d.customer_id IS NULL
    """)

    # dim_supplier
    cur.execute("""
        INSERT INTO dwh.dim_supplier (
            supplier_id, supplier_name, country, contact_email, rating, lead_time_days,
            active, valid_from, valid_to, is_current, supplier_hash
        )
        SELECT
            s.supplier_id, s.supplier_name, s.country, s.contact_email, s.rating, s.lead_time_days,
            s.active, NOW(), NULL, TRUE,
            md5(concat_ws('|', s.supplier_name, s.country, s.contact_email, s.rating, s.lead_time_days, s.active))
        FROM staging_clean.suppliers_clean s
        LEFT JOIN dwh.dim_supplier d ON d.supplier_id = s.supplier_id AND d.is_current = TRUE
        WHERE d.supplier_id IS NULL
    """)

    # dim_product
    cur.execute("""
        INSERT INTO dwh.dim_product (
            product_id, product_name, category, sub_category, unit_cost, unit_price,
            supplier_id, valid_from, valid_to, is_current, product_hash
        )
        SELECT
            p.product_id, p.product_name, p.category, p.sub_category, p.unit_cost, p.unit_price,
            p.supplier_id, NOW(), NULL, TRUE,
            md5(concat_ws('|', p.product_name, p.category, p.sub_category, p.unit_cost, p.unit_price, p.supplier_id))
        FROM staging_clean.products_clean p
        LEFT JOIN dwh.dim_product d ON d.product_id = p.product_id AND d.is_current = TRUE
        WHERE d.product_id IS NULL
    """)

    # dim_order_status (reference)
    cur.execute("""
        INSERT INTO dwh.dim_order_status(status_code)
        SELECT DISTINCT current_status
        FROM staging_clean.orders_clean
        WHERE current_status IS NOT NULL
        ON CONFLICT (status_code) DO NOTHING
    """)

    # Ajouter aussi les statuts provenant de l'historique
    cur.execute("""
        INSERT INTO dwh.dim_order_status(status_code)
        SELECT DISTINCT status
        FROM staging_clean.order_status_history_clean
        WHERE status IS NOT NULL
        ON CONFLICT (status_code) DO NOTHING
    """)

    # dim_ship_mode (reference)
    cur.execute("""
        INSERT INTO dwh.dim_ship_mode(ship_mode_code)
        SELECT DISTINCT ship_mode
        FROM staging_clean.orders_clean
        WHERE ship_mode IS NOT NULL
        ON CONFLICT (ship_mode_code) DO NOTHING
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(run_id: str):
    conn = get_dwh_conn()
    try:
        with conn.cursor() as cur:
            print("[transform] Phase 1 : normalisation...")
            normalize(cur, run_id)

            print("[transform] Phase 2 : deduplication / qualite...")
            issues = deduplicate(cur)
            print(f"[transform]   -> {issues}")

            print("[transform] Phase 3 : conformation dimensionnelle...")
            conform_dimensions(cur, run_id)

        conn.commit()
    finally:
        conn.close()

    print("[transform] Done")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    run(os.getenv("ETL_RUN_ID", "manual"))

"""
Pipeline ETL - Data Warehouse
==============================
Point d'entree unique pour executer le processus ETL complet.

Usage :
    python BI/run_pipeline.py            # pipeline complet
    python BI/run_pipeline.py --force    # forcer meme si aucun changement

Flux :
  Donnees brutes (API ERP)
        |
  Nettoyage (normalisation, deduplication)
        |
  Transformation (calcul CA, marge, conformation dimensionnelle)
        |
  Analyse (moyennes, tendances, alertes)
        |
  Rapport / Tableau de bord (affichage CLI)

Ce script :
  1. Charge la configuration depuis BI/.env
  2. Cree automatiquement la base DWH PostgreSQL si elle n'existe pas
  3. Applique le schema (staging + dimensions + faits + index)
  4. Execute les 3 etapes ETL (avec detection de changement) :
       Extract  -> donnees ERP via API REST gateway (auth JWT)
       Transform -> normalisation, deduplication, conformation
       Load     -> chargement dimensions et faits (schema etoile)
  5. Analyse et rapport (KPIs, tendances, alertes stock)
"""

import os
import sys
import pathlib
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

BI_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = BI_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else BI_DIR / ".env"
SCHEMA_PATH = BI_DIR / "datawarehouse" / "schema.sql"

# Add BI/ to sys.path so we can import etl modules
sys.path.insert(0, str(BI_DIR))

# ---------------------------------------------------------------------------
# Database bootstrap
# ---------------------------------------------------------------------------

def ensure_database_exists():
    """Cree la base DWH si elle n'existe pas encore."""
    db_name = os.environ["DWH_PGDATABASE"]
    host = os.environ.get("DWH_PGHOST", "localhost")
    port = int(os.environ.get("DWH_PGPORT", "5432"))
    user = os.environ["DWH_PGUSER"]
    password = os.environ["DWH_PGPASSWORD"]

    admin_conn = psycopg2.connect(host=host, port=port, dbname="postgres",
                                  user=user, password=password)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                print(f"[pipeline] Base '{db_name}' existe deja")
            else:
                safe_name = db_name.replace('"', '""')
                cur.execute(f'CREATE DATABASE "{safe_name}"')
                print(f"[pipeline] Base '{db_name}' creee")
    finally:
        admin_conn.close()


def apply_schema():
    """Applique le DDL du Data Warehouse (idempotent via IF NOT EXISTS)."""
    host = os.environ.get("DWH_PGHOST", "localhost")
    port = int(os.environ.get("DWH_PGPORT", "5432"))
    db_name = os.environ["DWH_PGDATABASE"]
    user = os.environ["DWH_PGUSER"]
    password = os.environ["DWH_PGPASSWORD"]

    conn = psycopg2.connect(host=host, port=port, dbname=db_name,
                            user=user, password=password)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            sql = SCHEMA_PATH.read_text(encoding="utf-8")
            cur.execute(sql)
            print(f"[pipeline] Schema applique ({SCHEMA_PATH.name})")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Connexion DWH helper
# ---------------------------------------------------------------------------

def get_dwh_conn():
    return psycopg2.connect(
        host=os.environ.get("DWH_PGHOST", "localhost"),
        port=int(os.environ.get("DWH_PGPORT", "5432")),
        dbname=os.environ["DWH_PGDATABASE"],
        user=os.environ["DWH_PGUSER"],
        password=os.environ["DWH_PGPASSWORD"],
    )


# ---------------------------------------------------------------------------
# Etape 4 : Analyse
# ---------------------------------------------------------------------------

def run_analysis(run_id: str):
    """Requetes analytiques sur le DWH et affichage des resultats."""
    conn = get_dwh_conn()
    results = {}
    try:
        with conn.cursor() as cur:
            # KPIs globaux
            cur.execute("""
                SELECT COUNT(DISTINCT order_id) AS nb_commandes,
                       COUNT(DISTINCT customer_key) AS nb_clients,
                       COALESCE(SUM(sales_amount), 0) AS ca_total,
                       COALESCE(SUM(profit_amount), 0) AS profit_total,
                       COALESCE(AVG(sales_amount), 0) AS panier_moyen,
                       CASE WHEN SUM(sales_amount) > 0
                            THEN ROUND(SUM(profit_amount) / SUM(sales_amount) * 100, 1)
                            ELSE 0 END AS marge_pct
                FROM dwh.fact_sales_order_line
            """)
            row = cur.fetchone()
            results["kpis"] = {
                "commandes": row[0], "clients": row[1],
                "ca_total": float(row[2]), "profit_total": float(row[3]),
                "panier_moyen": float(row[4]), "marge_pct": float(row[5]),
            }

            # Top 5 produits par CA
            cur.execute("""
                SELECT dp.product_name, dp.category,
                       SUM(f.sales_amount) AS ca, SUM(f.profit_amount) AS profit
                FROM dwh.fact_sales_order_line f
                JOIN dwh.dim_product dp ON f.product_key = dp.product_key AND dp.is_current = TRUE
                GROUP BY dp.product_name, dp.category
                ORDER BY ca DESC LIMIT 5
            """)
            results["top_products"] = cur.fetchall()

            # Top 5 clients par CA
            cur.execute("""
                SELECT dc.customer_name, dc.segment,
                       SUM(f.sales_amount) AS ca
                FROM dwh.fact_sales_order_line f
                JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
                GROUP BY dc.customer_name, dc.segment
                ORDER BY ca DESC LIMIT 5
            """)
            results["top_customers"] = cur.fetchall()

            # Repartition par segment
            cur.execute("""
                SELECT dc.segment,
                       COUNT(DISTINCT f.order_id) AS commandes,
                       SUM(f.sales_amount) AS ca
                FROM dwh.fact_sales_order_line f
                JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
                WHERE dc.segment IS NOT NULL
                GROUP BY dc.segment ORDER BY ca DESC
            """)
            results["segments"] = cur.fetchall()

            # Alertes stock (produits avec stock < 10)
            cur.execute("""
                SELECT dp.product_name, fi.quantity_on_hand, fi.stock_value
                FROM dwh.fact_inventory_snapshot fi
                JOIN dwh.dim_product dp ON fi.product_key = dp.product_key AND dp.is_current = TRUE
                JOIN dwh.dim_date dd ON fi.snapshot_date_key = dd.date_key
                WHERE dd.full_date = (SELECT MAX(d2.full_date) FROM dwh.dim_date d2
                                      WHERE EXISTS (SELECT 1 FROM dwh.fact_inventory_snapshot f2
                                                    WHERE f2.snapshot_date_key = d2.date_key))
                  AND fi.quantity_on_hand < 10
                ORDER BY fi.quantity_on_hand ASC LIMIT 10
            """)
            results["stock_alerts"] = cur.fetchall()

            # Tendance mensuelle (3 derniers mois)
            cur.execute("""
                SELECT dd.month_name || ' ' || dd.year_number AS mois,
                       SUM(f.sales_amount) AS ca,
                       COUNT(DISTINCT f.order_id) AS commandes
                FROM dwh.fact_sales_order_line f
                JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
                GROUP BY dd.year_number, dd.month_number, dd.month_name
                ORDER BY dd.year_number DESC, dd.month_number DESC LIMIT 6
            """)
            results["monthly_trend"] = list(reversed(cur.fetchall()))

            # Volumes DWH
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM dwh.fact_sales_order_line) AS fact_sales,
                    (SELECT COUNT(*) FROM dwh.fact_order_status_transition) AS fact_transitions,
                    (SELECT COUNT(*) FROM dwh.fact_inventory_snapshot) AS fact_inventory,
                    (SELECT COUNT(*) FROM dwh.dim_customer WHERE is_current = TRUE) AS dim_customers,
                    (SELECT COUNT(*) FROM dwh.dim_product WHERE is_current = TRUE) AS dim_products,
                    (SELECT COUNT(*) FROM dwh.dim_supplier WHERE is_current = TRUE) AS dim_suppliers
            """)
            row = cur.fetchone()
            results["volumes"] = {
                "fact_sales": row[0], "fact_transitions": row[1], "fact_inventory": row[2],
                "dim_customers": row[3], "dim_products": row[4], "dim_suppliers": row[5],
            }
    finally:
        conn.close()

    return results


# ---------------------------------------------------------------------------
# Etape 5 : Rapport CLI
# ---------------------------------------------------------------------------

def print_report(results: dict):
    """Affiche le rapport BI en mode texte."""
    kpis = results.get("kpis", {})
    W = 60

    print("\n" + "=" * W)
    print("  RAPPORT BI - TABLEAU DE BORD")
    print("=" * W)

    # KPIs
    print("\n--- KPIs globaux ---")
    print(f"  Chiffre d'affaires total : {kpis.get('ca_total', 0):>14,.2f}")
    print(f"  Profit total             : {kpis.get('profit_total', 0):>14,.2f}")
    print(f"  Marge                    : {kpis.get('marge_pct', 0):>13.1f} %")
    print(f"  Nombre de commandes      : {kpis.get('commandes', 0):>14,}")
    print(f"  Clients uniques          : {kpis.get('clients', 0):>14,}")
    print(f"  Panier moyen             : {kpis.get('panier_moyen', 0):>14,.2f}")

    # Tendance mensuelle
    trend = results.get("monthly_trend", [])
    if trend:
        print("\n--- Tendance mensuelle ---")
        print(f"  {'Mois':<15} {'CA':>14} {'Commandes':>10}")
        print(f"  {'-'*15} {'-'*14} {'-'*10}")
        for mois, ca, cmd in trend:
            print(f"  {mois:<15} {float(ca):>14,.2f} {cmd:>10,}")

    # Segments
    segments = results.get("segments", [])
    if segments:
        print("\n--- Repartition par segment ---")
        print(f"  {'Segment':<20} {'Commandes':>10} {'CA':>14}")
        print(f"  {'-'*20} {'-'*10} {'-'*14}")
        for seg, cmd, ca in segments:
            print(f"  {seg:<20} {cmd:>10,} {float(ca):>14,.2f}")

    # Top produits
    top_prod = results.get("top_products", [])
    if top_prod:
        print("\n--- Top 5 produits (par CA) ---")
        print(f"  {'Produit':<30} {'Categorie':<15} {'CA':>12} {'Profit':>12}")
        print(f"  {'-'*30} {'-'*15} {'-'*12} {'-'*12}")
        for name, cat, ca, profit in top_prod:
            print(f"  {name[:30]:<30} {(cat or '')[:15]:<15} {float(ca):>12,.2f} {float(profit):>12,.2f}")

    # Top clients
    top_cli = results.get("top_customers", [])
    if top_cli:
        print("\n--- Top 5 clients (par CA) ---")
        print(f"  {'Client':<30} {'Segment':<15} {'CA':>14}")
        print(f"  {'-'*30} {'-'*15} {'-'*14}")
        for name, seg, ca in top_cli:
            print(f"  {name[:30]:<30} {(seg or '')[:15]:<15} {float(ca):>14,.2f}")

    # Alertes stock
    alerts = results.get("stock_alerts", [])
    if alerts:
        print("\n--- Alertes stock (quantite < 10) ---")
        print(f"  {'Produit':<35} {'Stock':>6} {'Valeur':>12}")
        print(f"  {'-'*35} {'-'*6} {'-'*12}")
        for name, qty, val in alerts:
            print(f"  {name[:35]:<35} {qty:>6} {float(val):>12,.2f}")
    else:
        print("\n--- Alertes stock : aucune alerte ---")

    # Volumes DWH
    vols = results.get("volumes", {})
    print("\n--- Volumes Data Warehouse ---")
    print(f"  fact_sales_order_line      : {vols.get('fact_sales', 0):>8,}")
    print(f"  fact_order_status_transition: {vols.get('fact_transitions', 0):>8,}")
    print(f"  fact_inventory_snapshot    : {vols.get('fact_inventory', 0):>8,}")
    print(f"  dim_customer (actifs)      : {vols.get('dim_customers', 0):>8,}")
    print(f"  dim_product (actifs)       : {vols.get('dim_products', 0):>8,}")
    print(f"  dim_supplier (actifs)      : {vols.get('dim_suppliers', 0):>8,}")

    print("\n" + "=" * W)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    force = "--force" in sys.argv

    # 1. Charger environnement
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    else:
        print(f"[pipeline] ATTENTION: {ENV_PATH} introuvable, "
              "utilisation des variables d'environnement systeme")

    run_id = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
    os.environ["ETL_RUN_ID"] = run_id

    print("=" * 60)
    print(f"  ETL Pipeline  |  run_id = {run_id}")
    if force:
        print("  Mode : --force (ignore la detection de changement)")
    print("=" * 60)

    # 2. Bootstrap base + schema
    print("\n--- Preparation base de donnees ---")
    ensure_database_exists()
    apply_schema()

    # 3. Extract
    print("\n--- Etape 1/3 : Extract (API ERP) ---")
    from etl.extract import run as run_extract
    counts, data_changed = run_extract(run_id)

    # 4. Transform + Load (skip si aucun changement sauf --force)
    if data_changed or force:
        if not data_changed and force:
            print("\n[pipeline] --force : transform+load malgre aucun changement")

        print("\n--- Etape 2/3 : Transform (normaliser, deduplicer, conformer) ---")
        from etl.transform import run as run_transform
        run_transform(run_id)

        print("\n--- Etape 3/3 : Load (dimensions + faits) ---")
        from etl.load import run as run_load
        run_load(run_id)
    else:
        print("\n--- Etapes 2-3 ignorees (aucun changement dans les donnees source) ---")
        print("  Utilisez --force pour forcer le rechargement complet")

    # 5. Analyse + Rapport
    print("\n--- Etape 4 : Analyse et rapport ---")
    try:
        results = run_analysis(run_id)
        print_report(results)
    except Exception as exc:
        print(f"[pipeline] Rapport non disponible : {exc}")

    # 6. Resume
    print("\n" + "=" * 60)
    print(f"  Pipeline termine avec succes  |  run_id = {run_id}")
    print(f"  Donnees extraites : {counts}")
    print(f"  Changements detectes : {'OUI' if data_changed else 'NON'}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[pipeline] ERREUR: {exc}", file=sys.stderr)
        sys.exit(1)

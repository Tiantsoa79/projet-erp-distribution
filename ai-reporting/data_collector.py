"""
Collecteur de donnees depuis le DWH pour alimenter les analyses IA.

Fournit le contexte business (KPIs, tendances, segments, alertes)
necessaire a la generation d'insights et de recommandations.
"""

import os
import psycopg2
import pandas as pd
from typing import Dict


def get_dwh_conn():
    return psycopg2.connect(
        host=os.getenv("DWH_PGHOST", "localhost"),
        port=int(os.getenv("DWH_PGPORT", "5432")),
        dbname=os.getenv("DWH_PGDATABASE", "erp_distribution_dwh"),
        user=os.getenv("DWH_PGUSER", "postgres"),
        password=os.getenv("DWH_PGPASSWORD", ""),
    )


def collect_business_context() -> Dict:
    """Collecte l'ensemble du contexte business depuis le DWH."""
    conn = get_dwh_conn()
    ctx = {}
    try:
        ctx["kpis"] = _kpis(conn)
        ctx["monthly_trend"] = _monthly_trend(conn)
        ctx["top_products"] = _top_products(conn)
        ctx["top_customers"] = _top_customers(conn)
        ctx["segments"] = _segments(conn)
        ctx["stock_alerts"] = _stock_alerts(conn)
        ctx["geo_performance"] = _geo_performance(conn)
    finally:
        conn.close()
    return ctx


# ------------------------------------------------------------------
# Requetes individuelles
# ------------------------------------------------------------------

def _kpis(conn) -> Dict:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT order_id)       AS nb_commandes,
               COUNT(DISTINCT customer_key)   AS nb_clients,
               COALESCE(SUM(sales_amount), 0) AS ca_total,
               COALESCE(SUM(profit_amount), 0) AS profit_total,
               COALESCE(AVG(sales_amount), 0) AS panier_moyen,
               CASE WHEN SUM(sales_amount) > 0
                    THEN ROUND(SUM(profit_amount)/SUM(sales_amount)*100, 1)
                    ELSE 0 END AS marge_pct
        FROM dwh.fact_sales_order_line
    """)
    row = cur.fetchone()
    cur.close()
    return {
        "commandes": row[0], "clients": row[1],
        "ca_total": float(row[2]), "profit_total": float(row[3]),
        "panier_moyen": float(row[4]), "marge_pct": float(row[5]),
    }


def _monthly_trend(conn) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT dd.month_name || ' ' || dd.year_number AS mois,
               SUM(f.sales_amount) AS ca,
               COUNT(DISTINCT f.order_id) AS commandes,
               SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
        GROUP BY dd.year_number, dd.month_number, dd.month_name
        ORDER BY dd.year_number, dd.month_number
    """)
    rows = cur.fetchall()
    cur.close()
    return [{"mois": r[0], "ca": float(r[1]), "commandes": r[2],
             "profit": float(r[3])} for r in rows]


def _top_products(conn, limit=10) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT dp.product_name, dp.category,
               SUM(f.sales_amount) AS ca, SUM(f.profit_amount) AS profit,
               SUM(f.quantity) AS qty
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_product dp ON f.product_key = dp.product_key AND dp.is_current = TRUE
        GROUP BY dp.product_name, dp.category
        ORDER BY ca DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [{"produit": r[0], "categorie": r[1], "ca": float(r[2]),
             "profit": float(r[3]), "quantite": r[4]} for r in rows]


def _top_customers(conn, limit=10) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT dc.customer_name, dc.segment,
               SUM(f.sales_amount) AS ca,
               COUNT(DISTINCT f.order_id) AS commandes
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
        GROUP BY dc.customer_name, dc.segment
        ORDER BY ca DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [{"client": r[0], "segment": r[1], "ca": float(r[2]),
             "commandes": r[3]} for r in rows]


def _segments(conn) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT dc.segment, COUNT(DISTINCT f.order_id) AS commandes,
               SUM(f.sales_amount) AS ca, SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
        WHERE dc.segment IS NOT NULL
        GROUP BY dc.segment ORDER BY ca DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return [{"segment": r[0], "commandes": r[1], "ca": float(r[2]),
             "profit": float(r[3])} for r in rows]


def _stock_alerts(conn) -> list:
    cur = conn.cursor()
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
    rows = cur.fetchall()
    cur.close()
    return [{"produit": r[0], "stock": r[1], "valeur": float(r[2])} for r in rows]


def _geo_performance(conn) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT dg.region, SUM(f.sales_amount) AS ca,
               COUNT(DISTINCT f.order_id) AS commandes,
               SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_geography dg ON f.geography_key = dg.geography_key
        WHERE dg.region IS NOT NULL
        GROUP BY dg.region ORDER BY ca DESC LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    return [{"region": r[0], "ca": float(r[1]), "commandes": r[2],
             "profit": float(r[3])} for r in rows]

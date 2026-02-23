"""
ETL - Extract
==============
Extraction des donnees depuis l'ERP backend via les APIs REST du gateway.

Sources consommees (avec authentification JWT) :
  - GET /api/v1/customers         -> clients
  - GET /api/v1/suppliers         -> fournisseurs
  - GET /api/v1/catalog/products  -> produits
  - GET /api/v1/sales/orders      -> commandes (liste)
  - GET /api/v1/sales/orders/:id  -> detail commande (lignes + historique statut)

Justification :
  L'extraction passe par l'API REST (et non par acces direct a la base OLTP)
  pour respecter l'architecture SOA du projet et la separation des couches.
  Le gateway assure l'authentification et le routage vers les micro-services.

Destination : tables staging_raw.* dans la base DWH.
"""

import hashlib
import json
import os
import pathlib
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg2

CHECKSUM_FILE = pathlib.Path(__file__).resolve().parent.parent / ".etl_checksums.json"
ORCHESTRATOR_STATE_FILE = pathlib.Path(__file__).resolve().parent.parent / ".orchestrator_state.json"


# ---------------------------------------------------------------------------
# Connexion DWH
# ---------------------------------------------------------------------------

def get_dwh_conn():
    return psycopg2.connect(
        host=os.getenv("DWH_PGHOST", "localhost"),
        port=int(os.getenv("DWH_PGPORT", "5432")),
        dbname=os.getenv("DWH_PGDATABASE"),
        user=os.getenv("DWH_PGUSER"),
        password=os.getenv("DWH_PGPASSWORD"),
    )


# ---------------------------------------------------------------------------
# Helpers API REST
# ---------------------------------------------------------------------------

def api_request(method: str, path: str, token: Optional[str] = None,
                payload: Optional[Dict] = None) -> Dict:
    base_url = os.getenv("GATEWAY_BASE_URL", "http://localhost:4000").rstrip("/")
    url = f"{base_url}{path}"

    data = None
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API {e.code} on {path}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"API error on {path}: {e}") from e


def api_login() -> str:
    """Authentification via le gateway - retourne un token JWT."""
    username = os.getenv("ETL_API_USERNAME")
    password = os.getenv("ETL_API_PASSWORD")
    if not username or not password:
        raise RuntimeError("ETL_API_USERNAME / ETL_API_PASSWORD requis")

    resp = api_request("POST", "/api/v1/auth/login",
                       payload={"username": username, "password": password})
    token = resp.get("token")
    if not token:
        raise RuntimeError("Login OK mais pas de token dans la reponse")
    return token


def fetch_paginated(token: str, path: str, page_size: int = 200) -> List[Dict]:
    """Recupere toutes les pages d'un endpoint pagine."""
    offset = 0
    items: List[Dict] = []
    while True:
        qs = urlencode({"limit": page_size, "offset": offset})
        resp = api_request("GET", f"{path}?{qs}", token=token)
        batch = resp.get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return items


# ---------------------------------------------------------------------------
# Insertion staging_raw
# ---------------------------------------------------------------------------

def insert_rows(cur, table: str, rows: List[Dict], cols: List[str], run_id: str) -> int:
    if not rows:
        return 0
    placeholders = ",".join(["%s"] * (len(cols) + 1))
    col_list = ",".join(cols + ["etl_run_id"])
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    for row in rows:
        cur.execute(sql, tuple(row.get(c) for c in cols) + (run_id,))
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Change detection (checksums)
# ---------------------------------------------------------------------------

def _compute_checksum(data: List[Dict]) -> str:
    """Calcule un hash MD5 stable d'une liste de dicts (tri par cles + valeurs)."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def _load_checksums() -> Dict[str, str]:
    if CHECKSUM_FILE.exists():
        return json.loads(CHECKSUM_FILE.read_text(encoding="utf-8"))
    return {}


def _save_checksums(checksums: Dict[str, str]):
    CHECKSUM_FILE.write_text(json.dumps(checksums, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _notify_orchestrator(data_changed: bool, counts: Dict):
    """Notifie l'orchestrateur des changements de données"""
    try:
        state = {
            "timestamp": os.getenv("ETL_RUN_ID", "manual"),
            "data_changed": data_changed,
            "counts": counts,
            "last_run": pathlib.Path(__file__).resolve().parent.parent.name
        }
        
        # Écrire l'état pour l'orchestrateur
        with open(ORCHESTRATOR_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        
        if data_changed:
            print(f"[extract] Changements notifiés à l'orchestrateur: {counts}")
        else:
            print("[extract] Aucun changement, notification envoyée")
            
    except Exception as e:
        print(f"[extract] Erreur notification orchestrateur: {e}")


def run(run_id: str) -> Tuple[Dict[str, int], bool]:
    """Extrait les donnees API et les charge dans staging_raw.

    Returns:
        (counts, data_changed) - nombre de lignes par entite et flag si donnees ont change.
    """
    page_size = int(os.getenv("ETL_API_PAGE_SIZE", "200"))

    print("[extract] Login gateway...")
    token = api_login()

    print("[extract] Fetching customers, suppliers, products...")
    customers = fetch_paginated(token, "/api/v1/customers", page_size)
    suppliers = api_request("GET", "/api/v1/suppliers", token=token).get("items", [])
    products = fetch_paginated(token, "/api/v1/catalog/products", page_size)

    print("[extract] Fetching orders + details (lines, status history)...")
    order_summaries = fetch_paginated(token, "/api/v1/sales/orders", page_size)

    orders: List[Dict] = []
    order_lines: List[Dict] = []
    order_status_history: List[Dict] = []
    synth_id = 1

    for summary in order_summaries:
        oid = summary.get("order_id")
        if not oid:
            continue
        detail = api_request("GET", f"/api/v1/sales/orders/{oid}", token=token)
        orders.append(detail.get("order") or {})
        for line in detail.get("lines", []):
            line["order_id"] = oid
            order_lines.append(line)
        for st in detail.get("status_history", []):
            st["order_id"] = oid
            st["id"] = synth_id
            synth_id += 1
            order_status_history.append(st)

    # --- Change detection ---
    new_checksums = {
        "customers": _compute_checksum(customers),
        "suppliers": _compute_checksum(suppliers),
        "products": _compute_checksum(products),
        "orders": _compute_checksum(orders),
        "order_lines": _compute_checksum(order_lines),
        "order_status_history": _compute_checksum(order_status_history),
    }
    old_checksums = _load_checksums()
    data_changed = new_checksums != old_checksums

    if not data_changed:
        print("[extract] Aucun changement detecte depuis la derniere extraction")
        counts = {
            "customers": len(customers), "suppliers": len(suppliers),
            "products": len(products), "orders": len(orders),
            "order_lines": len(order_lines), "order_status_history": len(order_status_history),
        }
        # Notifier l'orchestrateur même sans changements
        _notify_orchestrator(data_changed, counts)
        return counts, False

    changed_entities = [k for k in new_checksums if new_checksums[k] != old_checksums.get(k)]
    print(f"[extract] Changements detectes sur : {', '.join(changed_entities)}")

    # Chargement staging_raw (full refresh : truncate + insert)
    conn = get_dwh_conn()
    counts = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE
                    staging_raw.customers_raw,
                    staging_raw.suppliers_raw,
                    staging_raw.products_raw,
                    staging_raw.orders_raw,
                    staging_raw.order_lines_raw,
                    staging_raw.order_status_history_raw;
            """)

            counts["customers"] = insert_rows(cur, "staging_raw.customers_raw", customers,
                ["customer_id","customer_name","segment","city","state","region","email","created_at","updated_at"], run_id)

            counts["suppliers"] = insert_rows(cur, "staging_raw.suppliers_raw", suppliers,
                ["supplier_id","supplier_name","country","contact_email","contact_phone",
                 "rating","lead_time_days","payment_terms","active","created_at","updated_at"], run_id)

            counts["products"] = insert_rows(cur, "staging_raw.products_raw", products,
                ["product_id","product_name","category","sub_category","unit_cost","unit_price",
                 "supplier_id","stock_quantity","reorder_level","reorder_quantity","warehouse_location",
                 "created_at","updated_at"], run_id)

            counts["orders"] = insert_rows(cur, "staging_raw.orders_raw", orders,
                ["order_id","customer_id","order_date","ship_date","current_status","ship_mode",
                 "country","city","state","postal_code","region","created_at","updated_at"], run_id)

            counts["order_lines"] = insert_rows(cur, "staging_raw.order_lines_raw", order_lines,
                ["row_id","order_id","product_id","quantity","discount","sales","unit_price","cost","profit",
                 "created_at","updated_at"], run_id)

            counts["order_status_history"] = insert_rows(cur, "staging_raw.order_status_history_raw", order_status_history,
                ["id","order_id","status","status_date","updated_by","created_at"], run_id)

        conn.commit()
    finally:
        conn.close()

    # Sauvegarder les checksums apres chargement reussi
    _save_checksums(new_checksums)
    
    # Notifier l'orchestrateur des changements
    _notify_orchestrator(data_changed, counts)

    print(f"[extract] Done: {counts}")
    return counts, data_changed


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    run(os.getenv("ETL_RUN_ID", "manual"))

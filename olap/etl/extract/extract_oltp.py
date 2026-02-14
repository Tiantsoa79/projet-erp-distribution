import json
import os
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg2


def get_olap_conn():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )


def api_request(method: str, path: str, token: Optional[str] = None, payload: Optional[Dict] = None) -> Dict:
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
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API HTTP error {error.code} on {path}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"API URL error on {path}: {error}") from error


def api_login() -> str:
    username = os.getenv("ETL_API_USERNAME")
    password = os.getenv("ETL_API_PASSWORD")
    if not username or not password:
        raise RuntimeError("ETL_API_USERNAME and ETL_API_PASSWORD are required for API extraction")

    response = api_request("POST", "/api/v1/auth/login", payload={"username": username, "password": password})
    token = response.get("token")
    if not token:
        raise RuntimeError("Login succeeded without token in response")
    return token


def fetch_paginated(token: str, path: str, page_size: int = 200) -> List[Dict]:
    offset = 0
    items: List[Dict] = []
    while True:
        query = urlencode({"limit": page_size, "offset": offset})
        response = api_request("GET", f"{path}?{query}", token=token)
        batch = response.get("items", [])
        if not batch:
            break
        items.extend(batch)

        if len(batch) < page_size:
            break
        offset += page_size
    return items


def truncate_raw_tables(cur):
    cur.execute(
        """
        TRUNCATE TABLE
          staging_raw.customers_raw,
          staging_raw.suppliers_raw,
          staging_raw.products_raw,
          staging_raw.orders_raw,
          staging_raw.order_lines_raw,
          staging_raw.order_status_history_raw;
        """
    )


def insert_rows(cur, table_name: str, rows: List[Dict], columns: List[str], run_id: str):
    if not rows:
        return 0

    placeholders = ",".join(["%s"] * (len(columns) + 1))
    cols = ",".join(columns + ["etl_run_id"])
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

    for row in rows:
        values = [row.get(column) for column in columns]
        cur.execute(sql, (*values, run_id))
    return len(rows)


def main():
    run_id = os.getenv("ETL_RUN_ID", "manual")
    page_size = int(os.getenv("ETL_API_PAGE_SIZE", "200"))

    token = api_login()

    customers = fetch_paginated(token, "/api/v1/customers", page_size)
    suppliers = api_request("GET", "/api/v1/suppliers", token=token).get("items", [])
    products = fetch_paginated(token, "/api/v1/catalog/products", page_size)

    order_summaries = fetch_paginated(token, "/api/v1/sales/orders", page_size)
    orders = []
    order_lines = []
    order_status_history = []
    synthetic_status_id = 1

    for summary in order_summaries:
        order_id = summary.get("order_id")
        if not order_id:
            continue

        detail = api_request("GET", f"/api/v1/sales/orders/{order_id}", token=token)
        order = detail.get("order") or {}
        orders.append(order)

        for line in detail.get("lines", []):
            line_copy = dict(line)
            line_copy["order_id"] = order_id
            order_lines.append(line_copy)

        for status in detail.get("status_history", []):
            status_copy = dict(status)
            status_copy["order_id"] = order_id
            status_copy["id"] = synthetic_status_id
            synthetic_status_id += 1
            order_status_history.append(status_copy)

    conn = get_olap_conn()
    extracted = {}
    try:
        with conn.cursor() as cur:
            truncate_raw_tables(cur)

            extracted["customers"] = insert_rows(
                cur,
                "staging_raw.customers_raw",
                customers,
                ["customer_id", "customer_name", "segment", "city", "state", "region", "email", "created_at", "updated_at"],
                run_id,
            )
            extracted["suppliers"] = insert_rows(
                cur,
                "staging_raw.suppliers_raw",
                suppliers,
                [
                    "supplier_id",
                    "supplier_name",
                    "country",
                    "contact_email",
                    "contact_phone",
                    "rating",
                    "lead_time_days",
                    "payment_terms",
                    "active",
                    "created_at",
                    "updated_at",
                ],
                run_id,
            )
            extracted["products"] = insert_rows(
                cur,
                "staging_raw.products_raw",
                products,
                [
                    "product_id",
                    "product_name",
                    "category",
                    "sub_category",
                    "unit_cost",
                    "unit_price",
                    "supplier_id",
                    "stock_quantity",
                    "reorder_level",
                    "reorder_quantity",
                    "warehouse_location",
                    "created_at",
                    "updated_at",
                ],
                run_id,
            )
            extracted["orders"] = insert_rows(
                cur,
                "staging_raw.orders_raw",
                orders,
                [
                    "order_id",
                    "customer_id",
                    "order_date",
                    "ship_date",
                    "current_status",
                    "ship_mode",
                    "country",
                    "city",
                    "state",
                    "postal_code",
                    "region",
                    "created_at",
                    "updated_at",
                ],
                run_id,
            )
            extracted["order_lines"] = insert_rows(
                cur,
                "staging_raw.order_lines_raw",
                order_lines,
                ["row_id", "order_id", "product_id", "quantity", "discount", "sales", "unit_price", "cost", "profit", "created_at", "updated_at"],
                run_id,
            )
            extracted["order_status_history"] = insert_rows(
                cur,
                "staging_raw.order_status_history_raw",
                order_status_history,
                ["id", "order_id", "status", "status_date", "updated_by", "created_at"],
                run_id,
            )

        conn.commit()
    finally:
        conn.close()

    print("Extract completed via gateway APIs", extracted)


if __name__ == "__main__":
    main()

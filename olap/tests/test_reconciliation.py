import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg2


def api_request(method, path, token=None, payload=None):
    base_url = os.getenv("GATEWAY_BASE_URL", "http://localhost:4000").rstrip("/")
    url = f"{base_url}{path}"
    data = None
    headers = {"content-type": "application/json"}

    if token:
        headers["authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def api_login():
    username = os.getenv("ETL_API_USERNAME")
    password = os.getenv("ETL_API_PASSWORD")
    if not username or not password:
        raise RuntimeError("ETL_API_USERNAME and ETL_API_PASSWORD are required")

    response = api_request("POST", "/api/v1/auth/login", payload={"username": username, "password": password})
    token = response.get("token")
    if not token:
        raise RuntimeError("Login response has no token")
    return token


def fetch_paginated_items(token, path, page_size=200):
    offset = 0
    items = []
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


def get_olap_conn():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )


def test_orders_vs_fact_rows_non_zero():
    olap = get_olap_conn()
    try:
        with olap.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM dwh.fact_sales_order_line")
            fact_rows = cur.fetchone()[0]
            assert fact_rows > 0, "No rows loaded in fact_sales_order_line"
    finally:
        olap.close()


def test_order_line_row_count_reasonable_gap():
    token = api_login()
    olap = get_olap_conn()
    try:
        order_summaries = fetch_paginated_items(token, "/api/v1/sales/orders")
        src_count = 0
        for order in order_summaries:
            order_id = order.get("order_id")
            if not order_id:
                continue
            detail = api_request("GET", f"/api/v1/sales/orders/{order_id}", token=token)
            src_count += len(detail.get("lines", []))

        with olap.cursor() as dst_cur:
            dst_cur.execute("SELECT COUNT(*) FROM dwh.fact_sales_order_line")
            dst_count = dst_cur.fetchone()[0]

            assert dst_count <= src_count + 1000, (
                f"Unexpectedly high destination row count: src={src_count}, dst={dst_count}"
            )
    finally:
        olap.close()

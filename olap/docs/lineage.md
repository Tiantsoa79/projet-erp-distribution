# Data Lineage (source -> staging -> DWH)

## Ventes

- `public.orders` + `public.order_lines`
  -> `staging_raw.orders_raw`, `staging_raw.order_lines_raw`
  -> `staging_clean.orders_clean`, `staging_clean.order_lines_clean`
  -> `dwh.fact_sales_order_line`

## Statuts de commande

- `public.order_status_history`
  -> `staging_raw.order_status_history_raw`
  -> `staging_clean.order_status_history_clean`
  -> `dwh.fact_order_status_transition`

## Produits et stock

- `public.products`
  -> `staging_raw.products_raw`
  -> `staging_clean.products_clean`
  -> `dwh.dim_product`, `dwh.fact_inventory_snapshot`

## Clients

- `public.customers`
  -> `staging_raw.customers_raw`
  -> `staging_clean.customers_clean`
  -> `dwh.dim_customer`

## Fournisseurs

- `public.suppliers`
  -> `staging_raw.suppliers_raw`
  -> `staging_clean.suppliers_clean`
  -> `dwh.dim_supplier`

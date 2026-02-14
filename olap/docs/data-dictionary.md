# Data Dictionary (initial)

## dwh.fact_sales_order_line

- Grain: 1 ligne de commande.
- Mesures: `quantity`, `sales_amount`, `cost_amount`, `profit_amount`, `discount_rate`.
- FK: `date_key`, `customer_key`, `product_key`, `supplier_key`, `status_key`, `ship_mode_key`, `geography_key`.

## dwh.fact_order_status_transition

- Grain: 1 transition de statut par commande et timestamp.
- Mesures: `transition_count` (1), `transition_delay_days` (optionnel).
- FK: `order_date_key`, `status_date_key`, `status_key`, `customer_key`.

## dwh.fact_inventory_snapshot

- Grain: 1 produit x date snapshot.
- Mesures: `stock_quantity`, `stock_value`.
- FK: `snapshot_date_key`, `product_key`, `supplier_key`.

## dwh.dim_customer (SCD2)

- BK: `customer_id`.
- Colonnes: `customer_name`, `segment`, `city`, `state`, `region`, `email`.
- SCD2: `valid_from`, `valid_to`, `is_current`.

## dwh.dim_product (SCD2)

- BK: `product_id`.
- Colonnes: `product_name`, `category`, `sub_category`, `unit_cost`, `unit_price`, `supplier_id`.
- SCD2: `valid_from`, `valid_to`, `is_current`.

## dwh.dim_supplier (SCD2)

- BK: `supplier_id`.
- Colonnes: `supplier_name`, `country`, `contact_email`, `rating`, `lead_time_days`, `active`.
- SCD2: `valid_from`, `valid_to`, `is_current`.

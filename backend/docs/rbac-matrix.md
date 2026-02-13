# Matrice RBAC (permission -> endpoints)

## Orders

- `orders.read`: `GET /api/v1/sales/*`
- `orders.create`: `POST /api/v1/sales/*` (hors transition)
- `orders.update`: `PATCH /api/v1/sales/*`
- `orders.delete`: `DELETE /api/v1/sales/*`
- `orders.transition`: `POST /api/v1/sales/orders/:orderId/transition`

## Products

- `products.read`: `GET /api/v1/catalog/*`
- `products.create`: `POST /api/v1/catalog/*`
- `products.update`: `PATCH /api/v1/catalog/products/:productId`
- `products.update_stock`: `PATCH /api/v1/catalog/*/stock`
- `products.delete`: `DELETE /api/v1/catalog/*`

## Suppliers

- `suppliers.read`: `GET /api/v1/suppliers/*`
- `suppliers.create`: `POST /api/v1/suppliers/*`
- `suppliers.update`: `PATCH /api/v1/suppliers/*`
- `suppliers.delete`: `DELETE /api/v1/suppliers/*`

## Customers

- `customers.read`: `GET /api/v1/customers/*`
- `customers.create`: `POST /api/v1/customers/*`
- `customers.update`: `PATCH /api/v1/customers/*`
- `customers.delete`: `DELETE /api/v1/customers/*`

## Administration / Audit

- `users.manage`: endpoints admin users
- `roles.manage`: endpoints admin roles et assignations
- `audit.read`: `GET /api/v1/audit/logs`

## Note

Le contrôle est appliqué dans la gateway avant forwarding.

# Backend ERP Distribution

Guide complet (debutant-friendly) pour lancer, tester et comprendre le backend ERP.

## 1) Vue d'ensemble

Le backend contient 5 services Node.js:

1. `gateway` (port 4000): point d'entree unique + auth JWT/cookie + controle RBAC
2. `sales` (port 4001)
3. `catalog` (port 4002)
4. `customers` (port 4003)
5. `suppliers` (port 4004)

Base de donnees: PostgreSQL (`erp_distribution`) alimentee par les CSV (`../data`).

## 2) Etat des iterations

### Iteration 1 (RBAC) - terminee

- Authentification basee DB (`users.password_hash`).
- Modele RBAC complet (`users`, `roles`, `permissions`, `user_roles`, `role_permissions`).
- JWT enrichi avec `roles` + `permissions`.
- Controle de permission par route au gateway.

### Iteration 2 (workflows + regles avancees) - terminee

- Machine d'etats commande controlee:
  - `Draft -> Submitted -> Approved -> Shipped -> Closed`
- Endpoint de transition: `POST /orders/:orderId/transition` (via gateway).
- Regles metier actives:
  - `ship_date >= order_date`
  - blocage de creation/transition en periode comptable `closed`
  - validations de coherence lignes (quantite, discount, sales, cost, profit)
- Table `accounting_periods` (`open` / `closed`) + seed automatique.

### Iteration 3 (auditabilite complete) - terminee

- Table `audit_logs` (who/when/what/before/after/request_id/source_service).
- Traçage automatique des mutations sensibles:
  - `order.create`
  - `order.transition`
  - `product.stock.update`
  - `supplier.update`
  - `customer.create`
  - `customer.update`
- Correlation request via `x-request-id` (gateway -> services).
- Endpoint de consultation audit avec filtres + export CSV:
  - `GET /api/v1/audit/logs`

## 3) Prerequis

- Node.js >= 18
- PostgreSQL local demarre
- Un utilisateur PostgreSQL valide (ex: `postgres`)

## 4) Configuration (.env)

1. Copier `backend/.env.example` -> `backend/.env`
2. Renseigner les vraies valeurs

Variables importantes:

```env
PGHOST=localhost
PGPORT=5432
PGDATABASE=erp_distribution
PGUSER=postgres
PGPASSWORD=your_password
CSV_DATA_DIR=../data

SALES_SERVICE_PORT=4001
CATALOG_SERVICE_PORT=4002
CUSTOMERS_SERVICE_PORT=4003
SUPPLIERS_SERVICE_PORT=4004
GATEWAY_PORT=4000

GATEWAY_JWT_SECRET=change_me_gateway
GATEWAY_JWT_EXPIRES_IN=8h
SESSION_COOKIE_NAME=erp_session
SESSION_COOKIE_SECURE=false

ADMIN_USER=your_admin_username
ADMIN_PASSWORD=your_admin_password

SALES_SERVICE_URL=http://localhost:4001
CATALOG_SERVICE_URL=http://localhost:4002
CUSTOMERS_SERVICE_URL=http://localhost:4003
SUPPLIERS_SERVICE_URL=http://localhost:4004
```

Important:
- `ADMIN_USER` / `ADMIN_PASSWORD` servent a creer/mettre a jour l'utilisateur admin RBAC au moment de `db:import`.
- Ne jamais commiter `.env`.

## 5) Installation + initialisation

Depuis `backend`:

```powershell
npm install
npm run db:import
```

Le script `db:import`:
- cree la DB si besoin,
- applique le schema SQL,
- initialise RBAC (roles/permissions/admin),
- initialise les periodes comptables (1 ouverte, 1 cloturee),
- importe les CSV seulement si pas deja presents (one-shot pour les donnees metier).

## 6) Lancer les services

### Tous les services

```powershell
npm run start:all
```

### Un service a la fois (debug)

```powershell
npm run gateway:start
npm run sales:start
npm run catalog:start
npm run customers:start
npm run suppliers:start
```

## 7) Verifier les health checks (hors gateway)

- `GET http://localhost:4001/health` (sales)
- `GET http://localhost:4002/health` (catalog)
- `GET http://localhost:4003/health` (customers)
- `GET http://localhost:4004/health` (suppliers)
- `GET http://localhost:4000/health` (gateway)

## 8) Tester via Gateway (Postman)

Base URL: `http://localhost:4000`

### Etape A - Login

`POST /api/v1/auth/login`

Body JSON (format):

```json
{
  "username": "<votre_admin_user>",
  "password": "<votre_admin_password>"
}
```

La reponse contient:
- `token` JWT,
- `user` (roles + permissions),
- cookie de session HTTP-only.

### Etape B - Verifier l'identite

`GET /api/v1/auth/me`

### Etape C - Voir la matrice de permissions exposee

`GET /api/v1/authz/matrix`

### Etape D - Appeler les routes metier

Exemples:
- `GET /api/v1/sales/orders`
- `POST /api/v1/sales/orders`
- `PATCH /api/v1/sales/orders/:orderId`
- `DELETE /api/v1/sales/orders/:orderId`
- `POST /api/v1/sales/orders/:orderId/transition`
- `GET /api/v1/admin/roles`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users`
- `GET /api/v1/admin/users/:userId/roles`
- `POST /api/v1/admin/users/:userId/roles`
- `DELETE /api/v1/admin/users/:userId/roles/:roleCode`
- `GET /api/v1/audit/logs?entity_type=order&actor_username=admin`
- `GET /api/v1/audit/logs?format=csv`
- `GET /api/v1/catalog/products`
- `POST /api/v1/catalog/products`
- `PATCH /api/v1/catalog/products/:productId`
- `PATCH /api/v1/catalog/products/:productId/stock`
- `DELETE /api/v1/catalog/products/:productId`
- `GET /api/v1/suppliers`
- `POST /api/v1/suppliers`
- `PATCH /api/v1/suppliers/:supplierId`
- `DELETE /api/v1/suppliers/:supplierId`
- `GET /api/v1/customers`
- `POST /api/v1/customers`
- `PATCH /api/v1/customers/:customerId`
- `DELETE /api/v1/customers/:customerId`

## 9) Permissions appliquees par le gateway

- Sales:
  - `GET` -> `orders.read`
  - `POST` -> `orders.create`
  - `PATCH` -> `orders.update`
  - `DELETE` -> `orders.delete`
  - `POST /orders/:orderId/transition` -> `orders.transition`
- Admin RBAC:
  - `GET /api/v1/admin/users` -> `users.manage`
  - `POST /api/v1/admin/users` -> `users.manage`
  - `GET /api/v1/admin/roles` -> `roles.manage`
  - `GET /api/v1/admin/users/:userId/roles` -> `roles.manage`
  - `POST /api/v1/admin/users/:userId/roles` -> `roles.manage`
  - `DELETE /api/v1/admin/users/:userId/roles/:roleCode` -> `roles.manage`
- Catalog:
  - `GET` -> `products.read`
  - `POST` -> `products.create`
  - `PATCH /products/:productId` -> `products.update`
  - `PATCH stock` -> `products.update_stock`
  - `DELETE` -> `products.delete`
- Suppliers:
  - `GET` -> `suppliers.read`
  - `POST` -> `suppliers.create`
  - `PATCH` -> `suppliers.update`
  - `DELETE` -> `suppliers.delete`
- Customers:
  - `GET` -> `customers.read`
  - `POST` -> `customers.create`
  - `PATCH` -> `customers.update`
  - `DELETE` -> `customers.delete`
- Audit:
  - `GET /api/v1/audit/logs` -> `audit.read`

Si la permission manque, le gateway renvoie `403 FORBIDDEN`.

## 10) Gestion users/roles via API (Admin RBAC)

Nouveaux endpoints admin:

1. `GET /api/v1/admin/roles`
   - liste les roles avec leurs permissions.
2. `GET /api/v1/admin/users`
   - liste les utilisateurs + roles.
3. `POST /api/v1/admin/users`
   - cree un utilisateur (`username`, `password`) avec `role_codes` optionnel.
4. `GET /api/v1/admin/users/:userId/roles`
   - liste des roles d'un utilisateur.
5. `POST /api/v1/admin/users/:userId/roles`
   - assigne un role via `role_code`.
6. `DELETE /api/v1/admin/users/:userId/roles/:roleCode`
   - retire un role.

Notes:

- ces endpoints sont proteges RBAC (`users.manage` / `roles.manage`),
- les operations sensibles (create user / assignation / retrait role) sont auditees.

## 11) Creation ergonomique (IDs auto + FK par nom)

Pour les endpoints de creation metier, l'API accepte maintenant des payloads plus simples:

- `supplier_id`, `customer_id`, `product_id`, `order_id` sont optionnels:
  - si absents, ils sont auto-generes selon un format coherent (`SUP-XXX`, `CU-XXXXX`, `PRD-AU-XXXXXXXX`, `OR-YYYY-XXXXXX`).
- Pour les cles etrangeres, vous pouvez envoyer un nom au lieu d'un ID:
  - produit: `supplier_name` (alternative a `supplier_id`),
  - commande: `customer_name` et `lines[].product_name` (alternatives aux IDs).

Si le nom n'existe pas, l'API renvoie une erreur metier explicite (`... not registered`).

## 12) Workflow de statut commande (Iteration 2)

Transitions autorisees uniquement:

1. `Draft -> Submitted`
2. `Submitted -> Approved`
3. `Approved -> Shipped`
4. `Shipped -> Closed`

Toute autre transition renvoie `422 INVALID_TRANSITION`.

## 13) Regles metier activees (Iteration 2)

### Creation commande

- `order_date` obligatoire au format `YYYY-MM-DD`
- `ship_date` optionnel, mais si present: `ship_date >= order_date`
- minimum 1 ligne
- `quantity` entier > 0
- `discount` entre 0 et 1
- `sales`, `cost`, `unit_price`, `profit` >= 0 (si fournis)
- coherence `sales ~ quantity * unit_price * (1 - discount)`
- coherence `profit ~ sales - cost * quantity`

Si une regle echoue: `422 BUSINESS_VALIDATION_FAILED`.

### Periodes comptables

- Si `order_date` tombe dans une periode `closed`:
  - creation commande bloquee (`409 PERIOD_CLOSED`)
  - transition de statut bloquee (`409 PERIOD_CLOSED`)

## 14) Verification SQL rapide

```sql
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM suppliers;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM order_lines;
SELECT COUNT(*) FROM order_status_history;

SELECT username, is_active FROM users;
SELECT role_code FROM roles ORDER BY role_code;
SELECT permission_code FROM permissions ORDER BY permission_code;
SELECT period_code, start_date, end_date, status FROM accounting_periods ORDER BY period_code;

SELECT audit_id, entity_type, entity_id, action, actor_username, request_id, source_service, created_at
FROM audit_logs
ORDER BY created_at DESC
LIMIT 20;
```

## 15) Consultation audit (Iteration 3)

Endpoint: `GET /api/v1/audit/logs`

Filtres disponibles:

- `entity_type` (order, product, supplier, customer, ...)
- `entity_id`
- `actor_username`
- `request_id`
- `source_service`
- `from` / `to` (timestamp)
- `limit` / `offset`
- `format=json|csv`

Exemples:

```text
GET /api/v1/audit/logs?entity_type=order&limit=10
GET /api/v1/audit/logs?request_id=<uuid>
GET /api/v1/audit/logs?from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z
GET /api/v1/audit/logs?format=csv
```

## 16) Scenarios d'acceptation (a executer dans Postman)

1. **Transition invalide -> 422**
   - creer/avoir une commande en `Draft`
   - appeler `POST /api/v1/sales/orders/{id}/transition` avec `{"to_status":"Shipped"}`
   - resultat attendu: `422 INVALID_TRANSITION`

2. **Periode cloturee -> 409**
   - prendre une date dans la periode seedee en `closed`
   - tenter `POST /api/v1/sales/orders` avec cette date
   - resultat attendu: `409 PERIOD_CLOSED`

3. **Regle date/metier -> 422**
   - tenter `POST /api/v1/sales/orders` avec `ship_date < order_date`
   - resultat attendu: `422 BUSINESS_VALIDATION_FAILED`

4. **Workflow valide -> 200**
   - enchainer les transitions autorisees
   - resultat attendu: 200 a chaque etape

5. **Audit genere a chaque mutation sensible**
   - executer: create order, transition, stock patch, supplier patch, customer create/update
   - verifier via `GET /api/v1/audit/logs`
   - resultat attendu: une entree audit par mutation

6. **Trace complete avant/apres**
   - prendre un `entity_id` depuis audit
   - verifier que `before_state` et `after_state` sont presents (pour update)
   - resultat attendu: retracage complet utilisateur + date + changement

7. **Export audit CSV**
   - appeler `GET /api/v1/audit/logs?format=csv`
   - resultat attendu: telechargement `audit_logs.csv`

8. **Gestion des roles via API admin -> 200**
   - creer un user via `POST /api/v1/admin/users`
   - assigner un role via `POST /api/v1/admin/users/{userId}/roles`
   - verifier les roles via `GET /api/v1/admin/users/{userId}/roles`

9. **Protection RBAC admin -> 403**
   - connecter un user sans `roles.manage`
   - appeler `POST /api/v1/admin/users/{userId}/roles`
   - resultat attendu: `403 FORBIDDEN`

## 16) Documentation OpenAPI

Fichier: `docs/swagger/openapi.yml`

Visualisation:
1. extension OpenAPI/Swagger dans l'IDE,
2. ou Swagger Editor (copier/coller le YAML).

## 17) Bonnes pratiques Git

- `.env` est ignore par git
- seul `.env.example` est versionne

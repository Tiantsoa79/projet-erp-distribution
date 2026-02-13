# Backend ERP Distribution

Guide complet pour lancer et tester le backend localement.

## 1) Ce que contient ce backend

Le backend est compose de 5 services Node.js :

1. `gateway` (port 4000) : point d'entree principal + auth JWT/cookie
2. `sales` (port 4001)
3. `catalog` (port 4002)
4. `customers` (port 4003)
5. `suppliers` (port 4004)

Base de donnees: PostgreSQL (`erp_distribution`), alimentee par les CSV du dossier `../data`.

## 2) Prerequis

- Node.js >= 18
- PostgreSQL local demarre
- Un utilisateur PostgreSQL valide (ex: `postgres`)

## 3) Configuration (.env)

1. Copier `backend/.env.example` vers `backend/.env`
2. Renseigner les vraies valeurs (DB + identifiants admin internes)

Exemple de variables attendues:

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
SESSION_COOKIE_NAME=erp_session
SESSION_COOKIE_SECURE=false

ADMIN_USER=your_admin_username
ADMIN_PASSWORD=your_admin_password

SALES_SERVICE_URL=http://localhost:4001
CATALOG_SERVICE_URL=http://localhost:4002
CUSTOMERS_SERVICE_URL=http://localhost:4003
SUPPLIERS_SERVICE_URL=http://localhost:4004
```

## 4) Installation et lancement

Depuis le dossier `backend`:

```powershell
npm install
```

### Import initial CSV -> PostgreSQL

```powershell
npm run db:import
```

Ce script:
- cree la base si besoin,
- cree le schema,
- importe les CSV,
- ne reimporte pas si des donnees existent deja (garde-fou one-shot).

### Lancer tous les services d'un coup

```powershell
npm run start:all
```

### Lancer un seul service (debug)

```powershell
npm run gateway:start
npm run sales:start
npm run catalog:start
npm run customers:start
npm run suppliers:start
```

## 5) Tests hors Gateway (health only)

Ces tests verifient que chaque microservice tourne bien directement:

- `GET http://localhost:4001/health` (sales)
- `GET http://localhost:4002/health` (catalog)
- `GET http://localhost:4003/health` (customers)
- `GET http://localhost:4004/health` (suppliers)
- `GET http://localhost:4000/health` (gateway)

## 6) Tests via Gateway (Postman recommande)

Base URL: `http://localhost:4000`

### Etape A - Login

Route: `POST /api/v1/auth/login`

Body JSON (exemple de format):

```json
{
  "username": "<votre_admin_user>",
  "password": "<votre_admin_password>"
}
```

Notes:
- les valeurs reelles viennent de `ADMIN_USER` et `ADMIN_PASSWORD` dans `.env`;
- ces identifiants sont internes a l'equipe et ne doivent pas etre publies.

### Etape B - Appeler les routes protegees

Tu peux utiliser:
- le cookie de session (automatique dans Postman), ou
- le token Bearer recu dans la reponse login.

Routes principales via gateway:

- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/sales/orders`
- `GET /api/v1/catalog/products`
- `GET /api/v1/suppliers`
- `GET /api/v1/customers`

## 7) Endpoints metier exposes (rappel)

- Sales: `/orders`, `/orders/:orderId`
- Catalog: `/products`, `/products/:productId`, `/products/:productId/stock`
- Suppliers: `/suppliers`, `/suppliers/:supplierId`
- Customers: `/customers`, `/customers/:customerId`

Depuis le gateway, ils sont prefixes par `/api/v1/...`.

## 8) Documentation API

Spec OpenAPI statique:

`docs/swagger/openapi.yml`

Tu peux la visualiser:
1. dans une extension OpenAPI/Swagger de l'IDE,
2. ou dans Swagger Editor (en collant le YAML).

## 9) Verifications SQL utiles

```sql
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM suppliers;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM order_lines;
SELECT COUNT(*) FROM order_status_history;
```

## 10) Bonnes pratiques Git

- `.env` ne doit jamais etre commit
- seul `.env.example` est versionne

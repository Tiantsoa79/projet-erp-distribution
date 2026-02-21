# API Reference - Interface OLAP

Documentation des endpoints REST de l'interface OLAP.

## Base URL
```
http://localhost:3030/api
```

## Dashboard Endpoints

### GET /dashboard/strategic
Retourne les données pour le dashboard stratégique.

**Response**
```json
{
  "kpis": {
    "ca_cur": 2261536.78,
    "ca_prev": 2100000.00,
    "ord_cur": 4922,
    "ord_prev": 4500,
    "cli_cur": 793,
    "cli_prev": 750,
    "avg_cur": 230.77,
    "avg_prev": 220.00
  },
  "monthly": [
    {"year_number": 2018, "month_number": 7, "month_name": "Juillet", "ca": 46270.92, "orders": 112, "profit": 12000.00}
  ],
  "segments": [
    {"segment": "Consumer", "nb_clients": 500, "ca": 1148060.53, "profit": 280000.00, "orders": 2537}
  ],
  "geo": [
    {"region": "Central", "ca": 850000.00, "orders": 2000, "profit": 200000.00}
  ],
  "products": [
    {"product_name": "Canon imageCLASS 2200", "category": "Technology", "ca": 61599.82, "qty": 150, "profit": 14909.63}
  ]
}
```

### GET /dashboard/tactical
Retourne les données pour le dashboard tactique.

**Response**
```json
{
  "daily": [
    {"full_date": "2018-07-01", "ca": 5000.00, "orders": 10, "clients": 8, "profit": 1200.00}
  ],
  "categories": [
    {"category": "Technology", "orders": 1500, "ca": 500000.00, "qty": 3000, "profit": 120000.00, "margin_pct": 24.0}
  ],
  "status": [
    {"status": "Delivered", "orders": 4000}
  ],
  "shipModes": [
    {"mode": "Standard Class", "orders": 3000, "ca": 800000.00, "avg_order": 266.67}
  ]
}
```

### GET /dashboard/operational
Retourne les données pour le dashboard opérationnel.

**Response**
```json
{
  "orders": [
    {"order_id": "ORD-001", "customer_name": "Sean Miller", "city": "New York", "region": "East", "status": "Delivered", "ship_mode": "Standard Class", "order_date": "2018-07-01", "total": 250.00}
  ],
  "stock": [
    {"product_name": "Product A", "category": "Category 1", "supplier_name": "Supplier A", "quantity_on_hand": 5, "stock_value": 500.00}
  ],
  "transitions": [
    {"status": "Delivered", "transitions": 4000}
  ],
  "geo": [
    {"region": "East", "orders": 1500, "ca": 400000.00}
  ]
}
```

## Pipeline Endpoints

### POST /pipeline/run
Démarre le pipeline ETL.

**Request Body**
```json
{
  "force": false  // true pour forcer le rechargement complet
}
```

**Response**
```json
{
  "message": "Pipeline demarre",
  "force": false
}
```

**Error Responses**
- `409 Conflict` : Pipeline déjà en cours
- `500 Internal Server Error` : Script non trouvé ou erreur d'exécution

### GET /pipeline/status
Retourne le statut actuel du pipeline et les logs.

**Response**
```json
{
  "status": "running",  // "idle" | "running" | "success" | "error"
  "running": true,
  "output": "=== Pipeline logs ===\nExtracting data..."
}
```

## Erreurs communes

### 401 Unauthorized
Non utilisé (pas d'authentification).

### 404 Not Found
Endpoint ou ressource introuvable.

### 500 Internal Server Error
Erreur serveur (base de données, script Python, etc.).

## Limites

- **Pas d'authentification** : Accès local uniquement
- **Pas de pagination** : Tous les retours sont complets
- **Pas de cache** : Chaque requête interroge la base

## Exemples d'utilisation

### JavaScript (frontend)
```javascript
// Récupérer les données stratégiques
const strategic = await fetch('/api/dashboard/strategic').then(r => r.json());

// Lancer le pipeline
await fetch('/api/pipeline/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ force: false })
});

// Vérifier le statut
const status = await fetch('/api/pipeline/status').then(r => r.json());
```

### cURL
```bash
# Dashboard stratégique
curl http://localhost:3030/api/dashboard/strategic

# Lancer le pipeline
curl -X POST http://localhost:3030/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Statut du pipeline
curl http://localhost:3030/api/pipeline/status
```

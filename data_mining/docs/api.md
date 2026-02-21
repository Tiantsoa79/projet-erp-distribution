# API Reference - Data Mining

Documentation des endpoints REST pour l'intégration web du module Data Mining.

## Base URL
```
http://localhost:3030/api/mining
```

## Endpoints

### GET /status
Retourne le statut du module Data Mining.

**Response**
```json
{
  "status": "ready",  // "ready" | "running" | "error"
  "last_run": "2024-02-21T16:30:00Z",
  "available_analyses": ["exploratory", "clustering", "anomaly", "rfm"],
  "results_available": true
}
```

### POST /run
Démarre une ou plusieurs analyses Data Mining.

**Request Body**
```json
{
  "analysis": "all",  // "exploratory" | "clustering" | "anomaly" | "rfm" | "all"
  "quick": false      // true pour mode rapide (échantillon)
}
```

**Response**
```json
{
  "run_id": "mining_20240221_163000",
  "status": "started",
  "analyses": ["exploratory", "clustering", "anomaly", "rfm"],
  "estimated_duration": "10-15 minutes"
}
```

### GET /results/latest
Retourne les résultats de la dernière exécution.

**Response**
```json
{
  "run_id": "mining_20240221_163000",
  "timestamp": "2024-02-21T16:30:00Z",
  "summary": {
    "exploratory": {
      "success": true,
      "total_records": 10000,
      "total_sales": 2261536.78
    },
    "clustering": {
      "success": true,
      "n_clusters": 4,
      "silhouette_score": 0.623
    },
    "anomaly": {
      "success": true,
      "n_anomalies": 487,
      "anomaly_rate": 4.87
    },
    "rfm": {
      "success": true,
      "n_customers": 793,
      "n_segments": 6
    }
  },
  "report_path": "results/reports/data_mining_report_20240221_163000.html"
}
```

### GET /results/clusters
Retourne les résultats du clustering client.

**Response**
```json
{
  "n_clusters": 4,
  "silhouette_score": 0.623,
  "clusters": [
    {
      "cluster_id": 0,
      "profile": "Clients VIP - Gros acheteurs fréquents",
      "n_customers": 156,
      "percentage": 19.7,
      "avg_ca_total": 5423.89,
      "avg_nb_commandes": 12.3,
      "avg_panier_moyen": 441.29
    }
  ]
}
```

### GET /results/anomalies
Retourne les anomalies détectées.

**Query Parameters**
- `limit` : Nombre d'anomalies à retourner (default: 50)
- `type` : Type d'anomalie (optional)

**Response**
```json
{
  "total_anomalies": 487,
  "anomaly_rate": 4.87,
  "anomaly_types": [
    {
      "type": "Montants élevés",
      "count": 156,
      "description": "Transactions > 2500.00€"
    }
  ],
  "anomalies": [
    {
      "order_key": "ORD-12345",
      "customer_name": "John Doe",
      "total_amount": 3456.78,
      "anomaly_score": -0.234,
      "reason": "Montant élevé"
    }
  ]
}
```

### GET /results/rfm
Retourne les segments RFM.

**Response**
```json
{
  "n_customers": 793,
  "segments": [
    {
      "segment": "Champions",
      "n_customers": 89,
      "percentage": 11.2,
      "avg_recency": 15.3,
      "avg_frequency": 8.7,
      "avg_monetary": 2345.67,
      "recommendation": "Programme VIP, offres exclusives"
    }
  ]
}
```

### GET /results/exploratory
Retourne les statistiques exploratoires.

**Response**
```json
{
  "summary": {
    "orders": {
      "total_records": 10000,
      "total_sales": 2261536.78,
      "avg_order_value": 226.15,
      "unique_customers": 793,
      "unique_regions": 4
    },
    "products": {
      "unique_products": 1861,
      "unique_categories": 17,
      "total_quantity_sold": 45000
    },
    "temporal": {
      "date_range": "2018-07-01 to 2018-12-31",
      "total_days": 184,
      "avg_daily_orders": 54.3,
      "best_day_sales": "2018-11-24"
    }
  }
}
```

### GET /plots/{plot_name}
Retourne un graphique spécifique.

**Available plots**
- `order_amounts_distribution`
- `sales_by_region`
- `top_products`
- `temporal_patterns`
- `correlation_matrix`
- `clustering_analysis`
- `anomaly_detection`
- `rfm_analysis`

**Response** : Image PNG (binary)

### GET /reports/latest
Retourne le dernier rapport HTML.

**Response** : HTML page

## Erreurs communes

### 400 Bad Request
```json
{
  "error": "Invalid analysis type",
  "message": "Analysis must be one of: exploratory, clustering, anomaly, rfm, all"
}
```

### 404 Not Found
```json
{
  "error": "Results not found",
  "message": "No mining results available. Run analysis first."
}
```

### 500 Internal Server Error
```json
{
  "error": "Analysis failed",
  "message": "Database connection error"
}
```

## Limites

- **Pas d'authentification** : Accès local uniquement
- **Pas de cache** : Chaque requête exécute l'analyse si nécessaire
- **Mode quick** : Échantillonnage 10% pour tests rapides

## Exemples d'utilisation

### JavaScript (frontend)
```javascript
// Démarrer toutes les analyses
const response = await fetch('/api/mining/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ analysis: 'all', quick: false })
});

// Vérifier les résultats
const results = await fetch('/api/mining/results/latest').then(r => r.json());

// Obtenir les clusters
const clusters = await fetch('/api/mining/results/clusters').then(r => r.json());
```

### cURL
```bash
# Lancer le clustering
curl -X POST http://localhost:3030/api/mining/run \
  -H "Content-Type: application/json" \
  -d '{"analysis": "clustering", "quick": true}'

# Obtenir les résultats
curl http://localhost:3030/api/mining/results/latest

# Télécharger un graphique
curl http://localhost:3030/api/mining/plots/clustering_analysis \
  --output clustering_analysis.png
```

## WebSocket (optionnel)

Pour le suivi en temps réel des analyses longues :

```javascript
const ws = new WebSocket('ws://localhost:3030/api/mining/ws');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Analysis progress:', update);
};
```

**Messages WebSocket**
```json
{
  "type": "progress",
  "analysis": "clustering",
  "progress": 0.6,
  "message": "Finding optimal clusters..."
}
```

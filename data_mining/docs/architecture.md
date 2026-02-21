# Architecture du Module Data Mining

## Vue d'ensemble

Le module Data Mining est une suite d'analyses avancées qui s'exécute sur le Data Warehouse ERP Distribution pour extraire des insights business pertinents.

## Stack technique

### Backend (Python)
- **Pandas** : Manipulation et analyse de données
- **NumPy** : Calculs numériques
- **Scikit-learn** : Algorithmes de Machine Learning
- **Matplotlib/Seaborn** : Visualisations
- **Plotly** : Graphiques interactifs
- **Jinja2** : Génération de rapports HTML

### Base de données
- **PostgreSQL** : Source de données (DWH)
- **psycopg2** : Connecteur PostgreSQL

## Structure des fichiers

```
data_mining/
├── run_mining.py              # Orchestrateur principal
├── exploratory_analysis.py    # Analyse exploratoire
├── clustering_analysis.py     # Clustering K-Means
├── anomaly_detection.py        # Détection d'anomalies
├── rfm_analysis.py            # Analyse RFM
├── report_generator.py        # Génération rapports HTML
├── requirements.txt           # Dépendances Python
├── .env.example              # Configuration environnement
├── results/                   # Sorties des analyses
│   ├── plots/                # Graphiques PNG
│   ├── reports/              # Rapports HTML
│   └── data/                 # Données exportées CSV
└── docs/                     # Documentation
```

## Flux de données

```
PostgreSQL DWH → Scripts Python → Analyses ML → Visualisations → Rapport HTML
        ↑                                    ↓
  Requêtes SQL                    Fichiers CSV/JSON/PNG
```

## Analyses implémentées

### 1. Analyse Exploratoire
- **Objectif** : Comprendre la structure et les patterns des données
- **Méthodes** : Statistiques descriptives, corrélations, distributions
- **Sorties** : Graphiques, tableaux résumés, données exportées

### 2. Clustering Clients
- **Objectif** : Identifier des segments naturels de clients
- **Algorithme** : K-Means avec optimisation du nombre de clusters
- **Métriques** : Silhouette score, inertie, profils de clusters

### 3. Détection d'Anomalies
- **Objectif** : Identifier transactions et comportements suspects
- **Algorithme** : Isolation Forest
- **Types** : Montants élevés, quantités inhabituelles, heures atypiques

### 4. Analyse RFM
- **Objectif** : Segmenter clients par valeur et comportement
- **Dimensions** : Récence, Fréquence, Montant
- **Segments** : Champions, fidèles, potentiels, à risque, perdus

## Pipeline d'exécution

```python
run_mining.py
├── Connexion DWH
├── Analyse Exploratoire
├── Clustering Clients
├── Détection Anomalies
├── Analyse RFM
└── Génération Rapport HTML
```

## Gestion des erreurs

- **Connexion DB** : Retry et fallback
- **Données manquantes** : Imputation et logging
- **Algorithmes ML** : Validation et paramètres par défaut
- **Génération rapports** : Templates par défaut

## Performance

- **Mode quick** : Échantillonnage pour tests rapides
- **Parallélisation** : Possible pour analyses indépendantes
- **Cache** : Résultats intermédiaires optionnels
- **Mémoire** : Gestion des grands datasets

## Évolution possible

- **Algorithmes supplémentaires** : ARIMA, Prophet, Deep Learning
- **API REST** : Endpoints pour intégration web
- **Dashboard** : Interface de visualisation interactive
- **Automatisation** : Orchestration avec Airflow/Luigi

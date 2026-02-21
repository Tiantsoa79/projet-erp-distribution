# Runbook - Data Mining

Guide d'exploitation pour le module Data Mining de l'ERP Distribution.

## 🚀 Démarrage

### Installation initiale

```powershell
cd data_mining
copy .env.example .env
# Éditer .env avec vos identifiants PostgreSQL DWH
pip install -r requirements.txt
```

### Exécution complète

```powershell
cd data_mining
python run_mining.py
```

### Exécution sélective

```powershell
# Analyse exploratoire uniquement
python run_mining.py --analysis exploratory

# Clustering uniquement
python run_mining.py --analysis clustering

# Détection anomalies uniquement
python run_mining.py --analysis anomaly

# Analyse RFM uniquement
python run_mining.py --analysis rfm

# Mode rapide (échantillon 10%)
python run_mining.py --quick
```

## 📋 Prérequis

### Base de données
- PostgreSQL local démarré
- Base `erp_distribution_dwh` existante et peuplée
- Tables DWH avec données suffisantes (min 1000 commandes)

### Configuration (.env)
```env
DWH_PGHOST=localhost
DWH_PGPORT=5432
DWH_PGDATABASE=erp_distribution_dwh
DWH_PGUSER=postgres
DWH_PGPASSWORD=votre_mot_de_passe

MINING_RESULTS_PATH=results
MINING_PLOTS_PATH=results/plots
MINING_REPORTS_PATH=results/reports
```

### Dépendances Python
```powershell
pip install pandas numpy psycopg2-binary scikit-learn matplotlib seaborn plotly jinja2
```

## 🔧 Utilisation

### Pipeline complet

Le pipeline exécute les 4 analyses dans l'ordre :
1. **Analyse Exploratoire** : Statistiques et visualisations
2. **Clustering Clients** : Segmentation K-Means
3. **Détection Anomalies** : Isolation Forest
4. **Analyse RFM** : Segmentation Récence-Fréquence-Montant
5. **Rapport HTML** : Synthèse complète

### Sorties générées

#### Graphiques (results/plots/)
- `order_amounts_distribution.png` - Distribution montants commandes
- `sales_by_region.png` - Ventes par région
- `top_products.png` - Top produits par ventes
- `temporal_patterns.png` - Patterns temporels
- `correlation_matrix.png` - Matrice corrélation
- `clustering_optimal_k.png` - Optimisation nombre clusters
- `clustering_analysis.png` - Analyse clustering complète
- `anomaly_detection.png` - Visualisation anomalies
- `rfm_analysis.png` - Analyse RFM
- `rfm_3d.png` - Vue 3D segments RFM

#### Données exportées (results/data/)
- `orders_summary.csv` - Résumé commandes
- `products_analysis.csv` - Analyse produits
- `temporal_patterns.csv` - Patterns temporels
- `customers_with_clusters.csv` - Clients avec clusters
- `cluster_statistics.csv` - Statistiques clusters
- `transactions_with_anomalies.csv` - Transactions avec anomalies
- `anomalies_only.csv` - Anomalies uniquement
- `rfm_analysis.csv` - Analyse RFM complète
- `rfm_segments.csv` - Segments RFM

#### Rapports (results/reports/)
- `data_mining_report_YYYYMMDD_HHMMSS.html` - Rapport HTML complet

## 🐛 Dépannage

### Erreurs fréquentes

#### "Erreur de connexion PostgreSQL"
- **Cause** : Mauvais identifiants dans `.env`
- **Solution** : Vérifier `DWH_PG*` variables, tester avec `psql`

#### "Pas assez de données"
- **Cause** : DWH vide ou trop peu de données
- **Solution** : Exécuter `python ../BI/run_pipeline.py` pour peupler le DWH

#### "ModuleNotFoundError"
- **Cause** : Dépendances manquantes
- **Solution** : `pip install -r requirements.txt`

#### "MemoryError"
- **Cause** : Dataset trop grand pour la RAM
- **Solution** : Utiliser `--quick` ou augmenter la RAM

#### "Erreur clustering"
- **Cause** : Pas assez de clients distincts
- **Solution** : Minimum 50 clients nécessaires pour K-Means

### Vérifications post-exécution

1. **Fichiers générés** : Vérifier que `results/` contient les 3 sous-dossiers
2. **Graphiques** : Ouvrir quelques PNG pour vérifier la génération
3. **Données CSV** : Vérifier que les fichiers ne sont pas vides
4. **Rapport HTML** : Ouvrir dans un navigateur pour validation

### Performance

#### Temps d'exécution typiques
- **Mode complet** : 5-15 minutes (selon volume données)
- **Mode quick** : 1-3 minutes
- **Analyse unique** : 1-5 minutes

#### Optimisations
- **Mode quick** : Échantillonnage 10% pour tests
- **Parallélisation** : Analyses indépendantes possibles
- **Cache** : Réutiliser les données entre analyses

## 📊 Interprétation des résultats

### Clustering
- **Silhouette score** : > 0.5 = bonne segmentation
- **Nombre optimal** : Choisir selon métier, pas seulement statistique
- **Profils clusters** : Interpréter les caractéristiques moyennes

### Anomalies
- **Taux normal** : 1-5% de transactions anormales
- **Types** : Montants élevés, heures inhabituelles, quantités étranges
- **Actions** : Vérification manuelle des cas suspects

### RFM
- **Champions** : Meilleurs clients, à conserver
- **Fidèles** : Base stable, programmes fidélité
- **À risque** : Campagnes réactivation
- **Perdus** : Campagnes reconquête

## 🔄 Maintenance

### Quotidienne
- Vérifier l'espace disque (graphiques et données peuvent s'accumuler)
- Nettoyer les anciens résultats si nécessaire

### Hebdomadaire
- Mettre à jour les dépendances `pip update`
- Vérifier les performances avec différents volumes de données

### Mensuelle
- Analyser les trends dans les résultats
- Ajuster les paramètres des algorithmes si nécessaire
- Archiver les anciens rapports

## 📞 Support

Pour toute question :
1. Consulter ce runbook
2. Vérifier les logs en console pour messages d'erreur détaillés
3. Tester avec `--quick` pour isoler les problèmes
4. Consulter la documentation technique dans `docs/architecture.md`

# Analytics Module - ERP Distribution

Ce module contient les analyses de data mining, les tableaux de bord BI et l'intelligence artificielle pour le système ERP Distribution.

## 📁 Structure

```
analytics/
├── 📄 __init__.py
├── 📁 data_mining/                   # Analyses Data Mining
│   ├── 📄 __init__.py
│   ├── 📄 rfm_segmentation.py        # Segmentation RFM
│   ├── 📄 kmeans_clustering.py       # Clustering K-Means
│   ├── 📄 anomaly_detection.py       # Détection anomalies
│   └── 📄 exploratory_analysis.py    # Analyse exploratoire
│
├── 📁 business_intelligence/         # Tableaux de bord & KPIs
│   ├── 📄 __init__.py
│   ├── 📄 kpis_calculator.py         # Calcul des KPIs
│   ├── 📄 dashboard_strategic.py     # Dashboard direction
│   ├── 📄 dashboard_tactical.py      # Dashboard managers
│   └── 📄 dashboard_operational.py   # Dashboard opérationnel
│
├── 📁 ai_reporting/                  # ⚠️ CRITIQUE - Reporting IA
│   ├── 📄 __init__.py
│   ├── 📄 insight_generator.py       # Génération insights auto
│   ├── 📄 recommendations.py         # Recommandations stratégiques
│   ├── 📄 storytelling.py            # Data storytelling
│   └── 📄 llm_integration.py         # Intégration LLM 
│
└── 📄 README.md                    # Ce fichier
```

## 🚀 Installation des dépendances

```bash
# Activer l'environnement virtuel OLAP
olap/venv/Scripts/activate

# Installer les dépendances analytics
pip install pandas numpy matplotlib seaborn scikit-learn plotly dash psycopg2-binary requests

# Pour l'IA (optionnel)
pip install openai anthropic
```

## 📊 Data Mining

### 1. Segmentation RFM
Analyse comportementale des clients basée sur Récence, Fréquence, Montant.

```bash
python analytics/data_mining/rfm_segmentation.py
```

**Résultats :**
- `analytics/data_mining/rfm_results.csv` - Segmentation clients
- `analytics/data_mining/rfm_segment_stats.csv` - Statistiques par segment

### 2. Clustering K-Means
Identification automatique de groupes de clients similaires.

```bash
python analytics/data_mining/kmeans_clustering.py
```

**Résultats :**
- `analytics/data_mining/clustering_results.csv` - Clustering clients
- `analytics/data_mining/clustering_stats.csv` - Statistiques clusters
- `analytics/data_mining/clustering_analysis.png` - Visualisations

### 3. Détection d'anomalies
Identification de transactions et comportements anormaux.

```bash
python analytics/data_mining/anomaly_detection.py
```

**Résultats :**
- `analytics/data_mining/transaction_anomalies.csv` - Transactions anormales
- `analytics/data_mining/customer_anomalies.csv` - Clients suspects
- `analytics/data_mining/temporal_anomalies.csv` - Anomalies temporelles

### 4. Analyse exploratoire
Vue d'ensemble complète des données et tendances.

```bash
python analytics/data_mining/exploratory_analysis.py
```

**Résultats :**
- Fichiers CSV détaillés par thématique
- `analytics/data_mining/exploratory_analysis.png` - Visualisations

## 📈 Business Intelligence

### 1. Calculateur de KPIs
Calcul des indicateurs clés de performance par période.

```bash
python analytics/business_intelligence/kpis_calculator.py
```

**KPIs calculés :**
- Financiers : CA, commandes, panier moyen
- Opérationnels : Taux livraison, temps traitement
- Clients : Actifs, inactifs, fidélité
- Produits : Vendus, catégories, fournisseurs

### 2. Dashboard Stratégique (Direction)
Vue d'ensemble pour la direction générale.

```bash
python analytics/business_intelligence/dashboard_strategic.py
```

**Accès :** http://localhost:8050

**Contenu :**
- KPIs principaux avec variations
- Évolution mensuelle du CA
- Répartition par segment client
- Performance géographique
- Top produits par CA

### 3. Dashboard Tactique (Managers)
Focus sur les opérations et performance équipes.

```bash
python analytics/business_intelligence/dashboard_tactical.py
```

**Accès :** http://localhost:8051

**Contenu :**
- Performance quotidienne
- Performance par équipe
- Analyse par catégorie produit
- Distribution statuts commandes

### 4. Dashboard Opérationnel (Équipes)
Actions quotidiennes et alertes en temps réel.

```bash
python analytics/business_intelligence/dashboard_operational.py
```

**Accès :** http://localhost:8052

**Contenu :**
- Alertes urgentes
- KPIs du jour
- Commandes récentes
- Alertes de stock
- Performance livraison

## 🤖 Intelligence Artificielle

### 1. Générateur d'Insights
Génération automatique d'insights business avec IA.

```bash
python analytics/ai_reporting/insight_generator.py
```

**Fonctionnalités :**
- Détection automatique de tendances
- Identification d'anomalies business
- Génération d'insights stratégiques
- Intégration LLM pour analyses avancées

### 2. Moteur de Recommandations
Génération de recommandations actionnables.

```bash
python analytics/ai_reporting/recommendations.py
```

**Types de recommandations :**
- Optimisation des prix
- Gestion des stocks
- Stratégies clients
- Actions marketing

### 3. Data Storytelling
Création d'histoires de données engageantes.

```bash
python analytics/ai_reporting/storytelling.py
```

**Sorties :**
- Histoires business narratives
- Visualisations thématiques
- Rapports Markdown/HTML

### 4. Intégration LLM
Interface avec différents modèles de langage.

```bash
python analytics/ai_reporting/llm_integration.py
```

**Providers supportés :**
- OpenAI (GPT-3.5/4)
- Anthropic (Claude)
- Modèles locaux (Ollama)

**Fonctionnalités :**
- Session interactive avec LLM
- Génération SQL depuis langage naturel
- Analyse business conversationnelle

## 🔧 Configuration

### Variables d'environnement
Les scripts utilisent le fichier `olap/configs/.env` :

```bash
# Base de données
OLAP_PGHOST=localhost
OLAP_PGPORT=5432
OLAP_PGDATABASE=erp_distribution
OLAP_PGUSER=postgres
OLAP_PGPASSWORD=mdp

# IA (optionnel)
OPENAI_API_KEY=votre_cle_openai
CLAUDE_API_KEY=votre_cle_claude
```

## 📋 Prérequis

- PostgreSQL avec le Data Warehouse peuplé
- Python 3.14+ avec les dépendances installées
- Environnement virtuel OLAP activé
- Clés API pour les fonctionnalités IA (optionnel)

## 🎯 Cas d'usage

### Direction Générale
- Dashboard stratégique pour décisions haut niveau
- Insights IA pour tendances marché
- Data storytelling pour présentations

### Managers
- Dashboard tactique pour gestion équipes
- Recommandations IA pour optimisation
- KPIs personnalisés par département

### Équipes Opérationnelles
- Dashboard opérationnel pour actions quotidiennes
- Alertes temps réel avec priorisation
- Accès rapide aux indicateurs clés

### Data Scientists
- Scripts data mining pour analyses avancées
- Interface LLM pour exploration données
- Outils de détection anomalies

### Utilisateurs IA
- Session interactive avec LLM
- Génération SQL depuis langage naturel
- Analyse business conversationnelle

## 🔄 Mise à jour

Les dashboards se rafraîchissent automatiquement :
- Stratégique : toutes les 5 minutes
- Tactique : toutes les minutes
- Opérationnel : toutes les 30 secondes

## 📊 Export des données

Tous les résultats peuvent être exportés en :
- CSV pour analyse dans Excel/Power BI
- PNG pour rapports visuels
- JSON pour intégration API
- Markdown pour documentation web

## 🚀 Lancement rapide

```bash
# 1. Activer l'environnement
olap/venv/Scripts/activate

# 2. Lancer tous les dashboards
python analytics/business_intelligence/dashboard_strategic.py &
python analytics/business_intelligence/dashboard_tactical.py &
python analytics/business_intelligence/dashboard_operational.py &

# 3. Lancer les analyses IA
python analytics/ai_reporting/insight_generator.py
python analytics/ai_reporting/recommendations.py
```

## 🎯 Architecture complète

L'ensemble du module analytics fournit :
- **Data Mining** : Analyses statistiques et ML
- **Business Intelligence** : Tableaux de bord interactifs
- **IA Légère** : Insights automatisés avec LLM en ligne
- **Intégration** : Interface unifiée avec l'ERP

**Le système est maintenant une solution d'analyse business complète et moderne !** 🚀

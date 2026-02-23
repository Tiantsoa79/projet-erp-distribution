# Projet ERP Distribution

**Projet d'examen - Master 1 Informatique**  
**INSI 2026**

## Contexte académique

Ce projet s'inscrit dans le cadre du cours de **Conception avancée d'un système ERP orienté services (SOA) et décisionnel (BI, Data Mining, Reporting et IA)**. Il vise à concevoir et urbaniser un système d'information d'entreprise intégrant :
- **Système ERP** pour la gestion opérationnelle
- **Architecture orientée services (SOA)** pour l'interopérabilité
- **Business Intelligence (BI)** pour l'aide à la décision
- **Data Mining** pour l'extraction de connaissances
- **Intelligence Artificielle (IA)** pour l'analyse avancée et le reporting intelligent

---

## LANCEMENT SIMPLIFIÉ (NOUVEAU)

### Installation automatisée en 1 commande 
```bash
python setup.py
```

### Lancement rapide en 1 commande 
```bash
venv\Scripts\activate
python start_all.py
```

---

## Description du projet

Système d'information intégré pour la gestion de stock et de distribution,
avec Business Intelligence, Data Mining et Reporting assisté par IA.

## Architecture du projet

```
projet-erp-distribution/
├── erp-api/            ERP Transactionnel (OLTP) - Architecture SOA
│   ├── services/           gateway, sales, catalog, customers, suppliers
│   ├── database/           connexion PostgreSQL
│   └── scripts/            import CSV, démarrage services
├── BI/                 Business Intelligence - ETL + Data Warehouse
│   ├── etl/                extract.py, transform.py, load.py
│   ├── datawarehouse/      schema.sql (staging + dimensions + faits)
│   └── run_pipeline.py     point d'entrée unique
├── data_mining/        Data Mining - Analyses avancées
│   ├── exploratory_analysis.py, clustering_analysis.py
│   ├── anomaly_detection.py, rfm_analysis.py
│   └── run_mining.py       point d'entrée unique
├── ai-reporting/       Reporting assisté par IA
│   ├── llm_client.py       client multi-provider (OpenAI, Claude, local)
│   ├── insight_generator.py, recommendations.py, storytelling.py
│   └── run_reporting.py    point d'entrée unique
├── interface_olap/     Interface Web Décisionnelle (frontend)
│   ├── server.js           serveur Express
│   ├── routes/             dashboard, pipeline, mining, ai
│   └── public/             SPA (HTML, CSS, JS)
├── data/               Jeux CSV sources
├── .env.example        Configuration unique (à copier en .env)
├── setup.py            Script d'installation automatisée
└── start_all.py        Script de lancement global
```

## Bases de données

| Base | Usage | Composant |
|-------|--------|------------|
| `erp_distribution` | OLTP transactionnel | erp-api |
| `erp_distribution_dwh` | Data Warehouse analytique | BI, Data Mining, AI, Interface |

---

## Démarrage rapide

### Prérequis
- **Node.js** >= 18
- **Python** >= 3.10 avec pip
- **PostgreSQL** >= 14 en cours d'exécution

### 1. Installation automatisée (RECOMMANDÉ) ⭐
```bash
git clone <url>
cd projet-erp-distribution

# ÉTAPE CRUCIALE - Configuration manuelle
copy .env.example .env
# Ouvrir .env et configurer :
# - Mots de passe PostgreSQL (DWH_PGPASSWORD)
# - Ports si conflits (GATEWAY_PORT, OLAP_PORT, etc.)
# - Clé Gemini si IA (GEMINI_API_KEY)

# Installation complète automatique
python setup.py
```

### 2. Lancement global
```bash
# Activer l'environnement
venv\Scripts\activate

# Lancer tous les services
python start_all.py
```

### 3. Accès aux services
- **ERP API** : http://localhost:4000 (Gateway + 4 micro-services)
- **Interface OLAP** : http://localhost:3030 (Tableaux de bord + Chat IA)

---

## 🤖 Chat IA - Configuration

### Option 1 - Utiliser votre propre clé API (RECOMMANDÉ) ⭐

Si la clé Gemini fournie ne fonctionne pas (quotas dépassés, restrictions géographiques) :

1. **Créez votre compte Google AI Studio** (gratuit) :
   - Allez sur : https://aistudio.google.com
   - Connectez-vous avec votre compte Google
   - Acceptez les conditions d'utilisation

2. **Obtenez votre clé API** :
   - Cliquez sur "Get API Key" dans le menu
   - Copiez votre clé personnelle

3. **Configurez votre clé dans `.env`** :
   ```bash
   # Remplacez la clé existante par la vôtre
   GEMINI_API_KEY=VOTRE_PROPRE_CLE_API_GEMINI
   ```

4. **Redémarrez les services** :
   ```bash
   # Arrêter (Ctrl+C) puis relancer
   python start_all.py
   ```

### Option 2 - Mode fallback (sans clé API)

Le chat IA fonctionne aussi **sans clé API** en mode fallback :
- Réponses basiques avec les données statiques
- Analyses business pertinentes
- Interface complètement fonctionnelle

**Note : Le mode fallback est automatique si la clé API ne fonctionne pas.**

---

## Fonctionnalités principales

### ERP API (`erp-api/`)
Architecture SOA avec :
- **Gateway** : authentification JWT, RBAC, routage, audit
- **Sales** : gestion commandes, lignes, statuts, workflows
- **Catalog** : produits, catégories, inventaire
- **Customers** : clients, segments, géographie
- **Suppliers** : fournisseurs, contacts, évaluations

### Business Intelligence (`BI/`)
- **Data Warehouse** : schéma en étoile (8 dimensions + 3 faits)
- **ETL automatique** : via API REST (respecte l'architecture SOA)
- **Détection incrémentale** : checksums MD5
- **Tableaux de bord** : stratégique, tactique, opérationnel

### Data Mining (`data_mining/`)
- **Analyse exploratoire** des données
- **Segmentation clients** : K-Means clustering
- **Détection d'anomalies** : Isolation Forest
- **Analyse RFM** : Récency, Frequency, Monetary

### AI Reporting (`ai-reporting/`)
- **Génération automatique d'insights**
- **Recommandations décisionnelles priorisées**
- **Data storytelling** (narration automatique)
- **Multi-provider** : OpenAI, Claude, Gemini, local (Ollama)

### Interface OLAP (`interface_olap/`)
Frontend décisionnel avec :
- **Pipeline** : exécution et suivi de l'ETL
- **Dashboards** : stratégique, tactique, opérationnel
- **Data Mining** : exécution et visualisation des analyses
- **AI Reporting** : insights, recommandations, storytelling
- **Chat IA** : Conversationnel avec Gemini (vraie IA !)

---

## Configuration

Un seul fichier `.env` à la racine du projet, divisé par sections :

1. **ERP API** : connexion OLTP, ports services, JWT
2. **BI / ETL** : connexion gateway, credentials, DWH
3. **Data Mining** : chemins résultats
4. **AI Reporting** : provider IA, clés API (optionnel)
5. **Interface OLAP** : port, chemins scripts

Voir `.env.example` pour la liste complète des variables.

---

## Automatisation

### Exécution quotidienne
```bash
# Automatisation complète (ETL + Data Mining + AI Reporting)
python daily_automation.py --schedule

# Exécution immédiate
python daily_automation.py
```

### Planification
- **Exécution** : tous les jours à 2h du matin
- **Détection des changements** : éviter les traitements inutiles
- **Logs avec rotation** : 10MB max, 5 backups
- **Mode dégradé** : fallback intelligent si erreurs

---

## Modules détaillés

### ERP API (`erp-api/`)
Noyau transactionnel SOA avec micro-services indépendants.

### Business Intelligence (`BI/`)
Data Warehouse analytique avec ETL depuis l'API REST.

### Data Mining (`data_mining/`)
Analyses avancées pour l'extraction de connaissances.

### AI Reporting (`ai-reporting/`)
Reporting intelligent avec génération automatique d'insights.

### Interface OLAP (`interface_olap/`)
Frontend moderne pour la visualisation et l'interaction.

---

## Notes importantes

- **Sécurité** : Mots de passe robustes, pas de clés API exposées
- **Performance** : Services optimisés, logs avec rotation
- **Scalabilité** : Architecture SOA pour l'évolution
- **Fonctionnement IA** : Vraie clé Gemini configurée, mode fallback si erreur
- **Chaque module** : exécutable indépendamment ou via l'interface

---

## Points forts du projet

 **Architecture moderne** : SOA + micro-services  
 **Intégration complète** : ERP + BI + Data Mining + IA  
 **Installation simplifiée** : Script `setup.py` automatisé  
 **Interface intuitive** : Tableaux de bord + Chat IA fonctionnel  
 **Sécurité renforcée** : Pas de secrets exposés  
 **Documentation complète** : README + guides d'utilisation  
 **Automatisation avancée** : Quotidienne avec détection changements  
 **Logs intelligents** : Rotation automatique et monitoring  
 **Multi-provider IA** : Gemini + OpenAI + Claude + Local  
 **Fonctionnalités avancées** : Data Mining + Reporting intelligent  

---

** Projet complet et prêt pour la production !**

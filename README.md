# Projet ERP Distribution

**Projet d'examen - Master 1 Informatique**  
**INSI 2026**

## Contexte academique

Ce projet s'inscrit dans le cadre du cours de **Conception avancee d'un systeme ERP oriente services (SOA) et decisionnel (BI, Data Mining, Reporting et IA)**. Il vise a concevoir et urbaniser un systeme d'information d'entreprise integrant :

- **Systeme ERP** pour la gestion operationnelle
- **Architecture orientee services (SOA)** pour l'interoperabilite
- **Business Intelligence (BI)** pour l'aide a la decision
- **Data Mining** pour l'extraction de connaissances
- **Intelligence Artificielle (IA)** pour l'analyse avancee et le reporting intelligent

### Equipe de developpement

- **Hasinjaka**
- **Miora**
- **Tiantsoa**
- **Tsiori**

---

## Description du projet

Systeme d'information integre pour la gestion de stock et de distribution,
avec Business Intelligence, Data Mining et Reporting assiste par IA.

## Architecture du projet

```
projet-erp-distribution/
  erp-api/            ERP Transactionnel (OLTP) - Architecture SOA
    services/           gateway, sales, catalog, customers, suppliers
    database/           connexion PostgreSQL
    scripts/            import CSV, demarrage services
  BI/                 Business Intelligence - ETL + Data Warehouse
    etl/                extract.py, transform.py, load.py
    datawarehouse/      schema.sql (staging + dimensions + faits)
    run_pipeline.py     point d'entree unique
  data_mining/        Data Mining - Analyses avancees
    exploratory_analysis.py, clustering_analysis.py
    anomaly_detection.py, rfm_analysis.py
    run_mining.py       point d'entree unique
  ai-reporting/       Reporting assiste par IA
    llm_client.py       client multi-provider (OpenAI, Claude, local)
    insight_generator.py, recommendations.py, storytelling.py
    run_reporting.py    point d'entree unique
  interface_olap/     Interface Web Decisionnelle (frontend)
    server.js           serveur Express
    routes/             dashboard, pipeline, mining, ai
    public/             SPA (HTML, CSS, JS)
  data/               Jeux CSV sources
  .env.example        Configuration unique (a copier en .env)
  start_all.py        Script de lancement global
```

## Bases de donnees

| Base | Usage | Composant |
|------|-------|-----------|
| `erp_distribution` | OLTP transactionnel | erp-api |
| `erp_distribution_dwh` | Data Warehouse analytique | BI, Data Mining, AI, Interface |

## Demarrage rapide

### Prerequis

- **Node.js** >= 18
- **Python** >= 3.10 avec pip
- **PostgreSQL** >= 14 en cours d'execution

### Installation

```powershell
# 1. Cloner le projet
git clone <url>
cd projet-erp-distribution

# 2. Configurer l'environnement
copy .env.example .env
# Editer .env avec vos parametres (ports, mots de passe PostgreSQL, etc.)

# 3. Installer les dependances Node.js
cd erp-api && npm install && cd ..
cd interface_olap && npm install && cd ..

# 4. Installer les dependances Python
pip install -r BI/requirements.txt
pip install -r data_mining/requirements.txt
pip install -r ai-reporting/requirements.txt

# 5. Importer les donnees CSV dans PostgreSQL
cd erp-api && npm run db:import && cd ..
```

### Lancement global

```powershell
python start_all.py
```

Cela demarre :
- **ERP API** sur http://localhost:4000 (gateway + 4 micro-services)
- **Interface OLAP** sur http://localhost:3030

### Lancement individuel

```powershell
# ERP API uniquement
cd erp-api && npm run start:all

# Interface OLAP uniquement
cd interface_olap && node server.js

# Pipeline ETL (BI)
python BI/run_pipeline.py
python BI/run_pipeline.py --force    # forcer le rechargement complet

# Data Mining
python data_mining/run_mining.py
python data_mining/run_mining.py --analysis clustering  # analyse specifique

# AI Reporting
python ai-reporting/run_reporting.py
python ai-reporting/run_reporting.py --no-ai   # mode statistique uniquement
python ai-reporting/run_reporting.py --json     # sortie JSON
```

## Modules

### ERP API (`erp-api/`)

Noyau transactionnel SOA avec :
- **Gateway** : authentification JWT, RBAC, routage, audit
- **Sales** : gestion commandes, lignes, statuts, workflows
- **Catalog** : produits, categories, inventaire
- **Customers** : clients, segments, geographie
- **Suppliers** : fournisseurs, contacts, evaluations

### Business Intelligence (`BI/`)

- Data Warehouse en **schema etoile** (8 dimensions, 3 faits)
- ETL automatise via API REST (respecte l'architecture SOA)
- Detection incrementale des changements (checksums MD5)
- Tableaux de bord : strategique, tactique, operationnel

### Data Mining (`data_mining/`)

- Analyse exploratoire des donnees
- Segmentation clients (K-Means clustering)
- Detection d'anomalies (Isolation Forest)
- Analyse RFM (Recency, Frequency, Monetary)

### AI Reporting (`ai-reporting/`)

- Generation automatique d'insights
- Recommandations decisionnelles priorisees
- Data storytelling (narration automatique)
- Fonctionne avec ou sans cle API (mode fallback statistique)

### Interface OLAP (`interface_olap/`)

Frontend decisionnelle avec :
- **Pipeline** : execution et suivi de l'ETL
- **Dashboards** : strategique, tactique, operationnel
- **Data Mining** : execution et visualisation des analyses
- **AI Reporting** : insights, recommandations, storytelling

## Configuration

Un seul fichier `.env` a la racine du projet, divise par sections :

1. **ERP API** : connexion OLTP, ports services, JWT
2. **BI / ETL** : connexion gateway, credentials, DWH
3. **Data Mining** : chemins resultats
4. **AI Reporting** : provider IA, cles API (optionnel)
5. **Interface OLAP** : port, chemins scripts

Voir `.env.example` pour la liste complete des variables.

## Notes

- Les fichiers `.env` sont ignores par Git (seuls les `.env.example` sont versionnes)
- L'ETL passe par l'API REST (pas d'acces direct a la base OLTP)
- L'AI Reporting fonctionne sans cle API (mode statistique fallback)
- Chaque module est executable independamment ou via l'interface

# BI - Data Warehouse, ETL & Analyse

Ce dossier contient le pipeline ETL, le Data Warehouse (schema en etoile) et le rapport d'analyse BI
du projet ERP Distribution. L'interface graphique des tableaux de bord se trouve dans `../interface_olap/`.

## Structure

```
BI/
├── .env.example              # Configuration (copier vers .env)
├── requirements.txt          # Dependances Python (psycopg2, dotenv)
├── run_pipeline.py           # Pipeline complet : ETL + Analyse + Rapport CLI
├── .etl_checksums.json       # Auto-genere : checksums pour detection de changement
├── etl/
│   ├── extract.py            # Extraction API REST (avec detection de changement)
│   ├── transform.py          # Normalisation, deduplication, conformation
│   └── load.py               # Chargement dimensions + faits dans le DWH
├── datawarehouse/
│   └── schema.sql            # DDL complet : staging + dimensions + faits + index
└── docs/
    ├── architecture.md       # Architecture technique, flux ETL, schema etoile
    ├── data-model.md         # Dictionnaire de donnees complet (staging + DWH)
    ├── governance.md         # Regles de gouvernance
    └── runbook.md            # Guide d'exploitation pas-a-pas
```

## Flux complet du pipeline

```
Donnees brutes (API ERP)
        |
  Nettoyage (normalisation, deduplication)
        |
  Transformation (calcul CA, marge, conformation dimensionnelle)
        |
  Analyse (moyennes, tendances, previsions)
        |
  Rapport / Tableau de bord (affichage CLI)
```

Le pipeline inclut desormais une **detection de changement** : si les donnees extraites depuis les APIs
sont identiques a la derniere extraction (comparaison par checksums MD5), les etapes Transform + Load
sont ignorees. Utilisez `--force` pour forcer un rechargement complet.

## Interface graphique : `interface_olap/`

Les tableaux de bord interactifs (strategique, tactique, operationnel) sont accessibles via une
interface web JavaScript separee dans le dossier `interface_olap/` a la racine du projet.

```powershell
cd interface_olap
npm install
npm start          # http://localhost:3030
```

Voir [`interface_olap/README.md`](../interface_olap/README.md) pour plus de details.

## Schema etoile (Data Warehouse)

**7 Dimensions :** `dim_date`, `dim_geography`, `dim_customer` (SCD2), `dim_supplier` (SCD2), `dim_product` (SCD2), `dim_order_status`, `dim_ship_mode`

**3 Faits :** `fact_sales_order_line` (ligne de commande), `fact_order_status_transition` (changement statut), `fact_inventory_snapshot` (stock quotidien)

## Execution

### Prerequis
- Python 3.10+
- PostgreSQL local
- Backend ERP demarre (`npm run start:all` dans `backend/`)

### Installation

```powershell
pip install -r BI/requirements.txt
copy BI\.env.example BI\.env
# Editer BI/.env avec vos identifiants
```

### Lancer le pipeline ETL + rapport

```powershell
python BI/run_pipeline.py            # pipeline intelligent (skip si aucun changement)
python BI/run_pipeline.py --force    # forcer le rechargement complet
```

Le pipeline affiche automatiquement a la fin :
- **KPIs globaux** (CA, profit, marge, commandes, clients, panier moyen)
- **Tendance mensuelle** (6 derniers mois)
- **Repartition par segment** client
- **Top 5 produits** et **Top 5 clients** par CA
- **Alertes stock** (produits avec quantite < 10)
- **Volumes DWH** (nombre de lignes par table)

### Variables d'environnement (BI/.env)

| Variable | Description |
|---|---|
| `GATEWAY_BASE_URL` | URL du gateway ERP (ex: `http://localhost:4000`) |
| `ETL_API_USERNAME` | Compte pour l'authentification API |
| `ETL_API_PASSWORD` | Mot de passe API |
| `DWH_PGHOST` | Hote PostgreSQL DWH |
| `DWH_PGPORT` | Port PostgreSQL DWH |
| `DWH_PGDATABASE` | Nom de la base DWH |
| `DWH_PGUSER` | Utilisateur PostgreSQL |
| `DWH_PGPASSWORD` | Mot de passe PostgreSQL |

## Documentation

| Document | Chemin | Description |
|---|---|---|
| **Architecture** | [`docs/architecture.md`](docs/architecture.md) | Architecture technique, flux ETL, schema etoile, interface, choix technologiques |
| **Modele de donnees** | [`docs/data-model.md`](docs/data-model.md) | Dictionnaire complet : staging raw/clean, 7 dimensions, 3 faits, index |
| **Gouvernance** | [`docs/governance.md`](docs/governance.md) | Regles ETL : normalisation, deduplication, separation OLTP/OLAP, tracabilite |
| **Runbook** | [`docs/runbook.md`](docs/runbook.md) | Guide d'exploitation pas-a-pas |

Commencer par le runbook pour toute premiere utilisation ou en cas de probleme.

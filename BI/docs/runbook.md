# Runbook d'exploitation - ETL / Data Warehouse

## 1. Prérequis

- Python 3.10+
- PostgreSQL local accessible
- ERP API démarrée (`npm run start:all` dans `erp-api/`)
- Dépendances Python installées (`pip install -r BI/requirements.txt`)
- Variables d'environnement configurées (`.env` a la racine du projet)

## 2. Installation initiale

```powershell
pip install -r BI/requirements.txt
copy .env.example .env
```

Éditer `.env` a la racine avec vos identifiants (section BI / ETL) :

| Variable | Exemple | Description |
|---|---|---|
| `GATEWAY_BASE_URL` | `http://localhost:4000` | URL du gateway ERP |
| `ETL_API_USERNAME` | `admin` | Compte API pour l'extraction |
| `ETL_API_PASSWORD` | `admin` | Mot de passe API |
| `DWH_PGHOST` | `localhost` | Hôte PostgreSQL DWH |
| `DWH_PGPORT` | `5432` | Port PostgreSQL DWH |
| `DWH_PGDATABASE` | `erp_distribution_dwh` | Nom de la base DWH |
| `DWH_PGUSER` | `postgres` | Utilisateur PostgreSQL |
| `DWH_PGPASSWORD` | `votre_mot_de_passe` | Mot de passe PostgreSQL |

## 3. Lancer le pipeline ETL

### Commande unique (tout automatisé)

```powershell
python BI/run_pipeline.py
```

Ce script fait tout automatiquement :

1. Crée la base `erp_distribution_dwh` si elle n'existe pas
2. Applique le schéma DDL (staging + dimensions + faits + index)
3. **Extract** : login gateway JWT → appels paginés vers les APIs ERP
4. **Transform** : normalisation, déduplication, conformation dimensionnelle
5. **Load** : chargement dimensions + 3 tables de faits (upsert idempotent)

### Sortie attendue

```
============================================================
  ETL Pipeline  |  run_id = run_20260221_101059
============================================================

--- Preparation base de donnees ---
[pipeline] Base 'erp_distribution_dwh' existe deja
[pipeline] Schema applique (schema.sql)

--- Etape 1/3 : Extract (API ERP) ---
[extract] Login gateway...
[extract] Fetching customers, suppliers, products...
[extract] Fetching orders + details (lines, status history)...
[extract] Done: {'customers': 793, 'suppliers': 50, 'products': 1861, ...}

--- Etape 2/3 : Transform (normaliser, deduplicer, conformer) ---
[transform] Phase 1 : normalisation...
[transform] Phase 2 : deduplication / qualite...
[transform]   -> {'customer_duplicates': 0, 'product_duplicates': 1, ...}
[transform] Phase 3 : conformation dimensionnelle...
[transform] Done

--- Etape 3/3 : Load (dimensions + faits) ---
[load] Chargement dimensions (date, geography)...
[load] Chargement faits (sales, transitions, inventory)...
[load] Done

============================================================
  Pipeline termine avec succes  |  run_id = run_20260221_101059
============================================================
```

## 4. Vérifications post-exécution

### 4.1 Volume chargé (psql)

```sql
\c erp_distribution_dwh

SELECT 'dim_date' AS table_name, COUNT(*) FROM dwh.dim_date
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dwh.dim_customer
UNION ALL SELECT 'dim_product', COUNT(*) FROM dwh.dim_product
UNION ALL SELECT 'dim_supplier', COUNT(*) FROM dwh.dim_supplier
UNION ALL SELECT 'dim_geography', COUNT(*) FROM dwh.dim_geography
UNION ALL SELECT 'fact_sales_order_line', COUNT(*) FROM dwh.fact_sales_order_line
UNION ALL SELECT 'fact_status_transition', COUNT(*) FROM dwh.fact_order_status_transition
UNION ALL SELECT 'fact_inventory_snapshot', COUNT(*) FROM dwh.fact_inventory_snapshot;
```

### 4.2 Intégrité dimensionnelle

```sql
-- Vérifier qu'il n'y a pas de FK nulles critiques
SELECT COUNT(*) AS null_customer_keys
FROM dwh.fact_sales_order_line WHERE customer_key IS NULL;

SELECT COUNT(*) AS null_product_keys
FROM dwh.fact_sales_order_line WHERE product_key IS NULL;
```

### 4.3 Qualité métier

```sql
-- Remises invalides
SELECT COUNT(*) FROM dwh.fact_sales_order_line
WHERE discount_rate IS NOT NULL AND (discount_rate < 0 OR discount_rate > 1);

-- Montants négatifs
SELECT COUNT(*) FROM dwh.fact_sales_order_line
WHERE sales_amount < 0 OR cost_amount < 0;
```

## 5. Exécuter une étape individuelle

Chaque module ETL peut être exécuté seul (utile pour debug) :

```powershell
python BI/etl/extract.py      # Extraction seule
python BI/etl/transform.py    # Transformation seule
python BI/etl/load.py         # Chargement seul
```

Note : chaque script charge `BI/.env` automatiquement quand exécuté directement.

## 6. Re-exécution (idempotence)

Le pipeline est **idempotent** : il peut être relancé à tout moment.

- `staging_raw` : TRUNCATE + INSERT (full-refresh)
- `staging_clean` : TRUNCATE + INSERT (full-refresh)
- `dwh` faits : ON CONFLICT DO UPDATE (upsert)
- `dwh` dimensions : ON CONFLICT DO NOTHING (insert si absent)

Relancer simplement :

```powershell
python BI/run_pipeline.py
```

## 7. Dépannage

### 7.1 Erreur connexion gateway (login échoue)

- Vérifier que l'ERP API est démarrée (`npm run start:all` dans `erp-api/`)
- Vérifier `GATEWAY_BASE_URL` dans `.env` racine
- Vérifier `ETL_API_USERNAME` / `ETL_API_PASSWORD`
- Tester manuellement : `curl http://localhost:4000/health`

### 7.2 Erreur connexion PostgreSQL DWH

- Vérifier que PostgreSQL est démarré
- Vérifier `DWH_PGHOST`, `DWH_PGPORT`, `DWH_PGUSER`, `DWH_PGPASSWORD`
- Tester : `psql -h localhost -U postgres -l`

### 7.3 Erreur 401/403 sur les APIs

- Le compte ETL n'a pas les permissions RBAC nécessaires
- Vérifier les rôles/permissions dans le backend (`GET /api/v1/admin/users`)
- Utiliser un compte admin pour l'ETL

### 7.4 Extraction vide (0 rows)

- Vérifier que `npm run db:import` a été exécuté dans `erp-api/`
- Tester un endpoint manuellement : `curl -H "Authorization: Bearer <token>" http://localhost:4000/api/v1/customers?limit=1`

### 7.5 Erreur FK violation au load

- Une date référencée dans les faits n'existe pas dans `dim_date`
- Normalement géré automatiquement (toutes les dates staging + CURRENT_DATE sont insérées)
- Si persistant : vérifier les données staging_clean

### 7.6 ModuleNotFoundError (psycopg2, dotenv)

```powershell
pip install -r BI/requirements.txt
```

## 8. Détection de changement (ETL incrémental)

Le pipeline détecte automatiquement si les données source ont changé depuis la dernière exécution.

### Comportement

- À chaque extraction, un **checksum MD5** est calculé par entité.
- Les checksums sont stockés dans `BI/.etl_checksums.json`.
- Si aucun changement → Transform + Load sont **ignorés** (gain de temps).
- Le rapport BI est toujours affiché, même sans changement.

### Forcer le rechargement

```powershell
python BI/run_pipeline.py --force
```

### Réinitialiser les checksums

Supprimer le fichier pour forcer un rechargement complet au prochain run :

```powershell
del BI\.etl_checksums.json
python BI/run_pipeline.py
```

## 9. Interface OLAP (`interface_olap/`)

Pour la documentation complète de l'interface web, consultez :
`interface_olap/docs/` (README, architecture, runbook, API reference)

### Démarrage rapide

```powershell
cd interface_olap
npm install
npm start
# Ouvrir http://localhost:3030
```

## 10. Checklist d'exploitation

### Avant exécution pipeline

- [ ] PostgreSQL démarré
- [ ] ERP API démarrée (`npm run start:all` dans `erp-api/`) — requis pour l'extraction
- [ ] `.env` racine configuré
- [ ] Dépendances Python installées (`pip install -r BI/requirements.txt`)

### Après pipeline ETL

- [ ] Message "Pipeline termine avec succes" affiché
- [ ] Rapport BI affiché (KPIs, tendances, alertes)
- [ ] Volumes des faits > 0
- [ ] Pas d'anomalies métier (remises, montants)

### Après lancement interface OLAP

Voir `interface_olap/docs/runbook.md` pour le dépannage complet.

- [ ] `http://localhost:3030` accessible
- [ ] Dashboard stratégique affiche les KPIs et graphiques
- [ ] Dashboard tactique affiche les tendances quotidiennes
- [ ] Dashboard opérationnel affiche les commandes et alertes stock

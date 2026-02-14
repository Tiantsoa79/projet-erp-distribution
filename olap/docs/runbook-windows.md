# Runbook OLAP (Windows) - ERP Distribution

Ce runbook decrit l'exploitation complete de la chaine:

1. ERP OLTP/SOA (`backend/`) demarre,
2. extraction via API REST gateway avec auth/token,
3. transformation ETL,
4. chargement Data Warehouse (schema en etoile),
5. controles qualite et reconciliation.

---

## 1) Scope et architecture

- Source: APIs REST du backend via gateway (`http://localhost:4000/api/v1/*`).
- Cible: base OLAP PostgreSQL (recommandee: `erp_distribution_olap`).
- Staging: `staging_raw`, `staging_clean`.
- DWH: `dwh`.

Scripts principaux:

- Orchestration: `olap/etl/orchestration/run_pipeline.py`
- Extract API: `olap/etl/extract/extract_oltp.py`
- Transform: `olap/etl/transform/*.py`
- Load DWH: `olap/etl/load/*.py`

---

## 2) Prerequis

### Technique

- Windows + PowerShell
- Python 3.10+
- PostgreSQL local
- Backend ERP fonctionnel (`backend/`)

### Comptes et droits

- Compte API ETL (doit pouvoir lire les endpoints via RBAC):
  - `customers.read`
  - `suppliers.read`
  - `products.read`
  - `orders.read`
- Compte DB OLAP avec droits CREATE/INSERT/UPDATE/DELETE sur schemas OLAP.

---

## 3) Preparation initiale (one-time)

### 3.1 Installer dependances Python

Depuis la racine du repo:

```powershell
python -m pip install -r olap/requirements.txt
```

### 3.2 Configurer l'environnement ETL

Copier et adapter:

```powershell
copy olap\configs\.env.example olap\configs\.env
```

Variables critiques:

- `GATEWAY_BASE_URL` (ex: `http://localhost:4000`)
- `ETL_API_USERNAME`
- `ETL_API_PASSWORD`
- `OLAP_PG*`

### 3.3 Creer la base OLAP si necessaire

Exemple (si besoin):

```sql
CREATE DATABASE erp_distribution_olap;
```

### 3.4 Creer schemas/tables OLAP

Executer dans cet ordre:

1. `olap/sql/staging/001_create_staging.sql`
2. `olap/sql/dwh/010_create_dimensions.sql`
3. `olap/sql/dwh/020_create_facts.sql`
4. `olap/sql/dwh/030_indexes_constraints.sql`

---

## 4) Demarrage operationnel standard

## Etape A - demarrer le backend ERP

Depuis `backend/`:

```powershell
npm install
npm run db:import
npm run start:all
```

Verifier:

- `GET http://localhost:4000/health`

## Etape B - lancer un run ETL

Depuis la racine du repo:

```powershell
python olap/etl/orchestration/run_pipeline.py
```

Ce script lance:

1. extract (API gateway + token),
2. normalize,
3. deduplicate,
4. conform_dimensions,
5. load_dimensions,
6. load_facts.

## Etape C - controles post-run

- Log technique: `olap/reports/etl_run_log.csv`
- Rapport qualite: `olap/reports/data_quality_report.md`

Executer tests:

```powershell
pytest olap/tests -q
```

---

## 5) Validation fonctionnelle rapide

### 5.1 Volume charge

```sql
SELECT COUNT(*) FROM dwh.fact_sales_order_line;
SELECT COUNT(*) FROM dwh.fact_order_status_transition;
SELECT COUNT(*) FROM dwh.fact_inventory_snapshot;
```

### 5.2 Integrite dimensionnelle

```sql
SELECT COUNT(*) AS null_customer_keys
FROM dwh.fact_sales_order_line
WHERE customer_key IS NULL;

SELECT COUNT(*) AS null_product_keys
FROM dwh.fact_sales_order_line
WHERE product_key IS NULL;
```

### 5.3 Qualite metier

```sql
SELECT COUNT(*) AS invalid_discount
FROM dwh.fact_sales_order_line
WHERE discount_rate IS NOT NULL AND (discount_rate < 0 OR discount_rate > 1);
```

---

## 6) Gouvernance et conformite (Partie B + C)

Couverts par le runbook:

- separation operationnel/analytique (backend vs olap),
- extraction via APIs SOA securisees,
- normalisation et dedoublonnage,
- controles qualite,
- DWH dimensionnel en etoile,
- pipeline ETL documente et automatisable.

---

## 7) Planification automatique (Windows Task Scheduler)

Objectif: run quotidien (ex: 01:00).

Commande a planifier:

```powershell
python D:\INSI\BI & Analytics\PROJET\github\projet-erp-distribution\olap\etl\orchestration\run_pipeline.py
```

Important:

- configurer le "Start in" sur la racine du repo;
- charger les variables d'environnement avant execution (script wrapper `.ps1` recommande);
- conserver logs stdout/stderr.

Exemple wrapper `run_olap_etl.ps1`:

```powershell
$env:GATEWAY_BASE_URL = "http://localhost:4000"
$env:ETL_API_USERNAME = "etl_admin_user"
$env:ETL_API_PASSWORD = "etl_admin_password"
$env:OLAP_PGHOST = "localhost"
$env:OLAP_PGPORT = "5432"
$env:OLAP_PGDATABASE = "erp_distribution_olap"
$env:OLAP_PGUSER = "postgres"
$env:OLAP_PGPASSWORD = "change_me"
python "D:\INSI\BI & Analytics\PROJET\github\projet-erp-distribution\olap\etl\orchestration\run_pipeline.py"
```

---

## 8) Troubleshooting

## Probleme: login API ETL echoue (401/403)

Verifier:

- `ETL_API_USERNAME` / `ETL_API_PASSWORD`
- permissions RBAC du compte ETL
- gateway demarre

## Probleme: extract vide

Verifier:

- endpoints `/api/v1/*` accessibles avec le compte ETL
- pagination (`ETL_API_PAGE_SIZE`)
- presence de donnees metier cote ERP

## Probleme: erreurs SQL de load

Verifier:

- scripts SQL executes dans l'ordre (staging -> dimensions -> facts -> indexes)
- structure des tables `staging_clean`
- contraintes d'unicite / FK

## Probleme: facts dupliques

Verifier:

- contraintes uniques DWH actives
- logique `ON CONFLICT` des loads
- rerun pipeline avec meme run_id pour reproduire

---

## 9) Procedure de re-run propre

1. Corriger config/code.
2. Relancer pipeline.
3. Verifier `etl_run_log.csv` (ligne SUCCESS).
4. Rejouer tests `pytest olap/tests -q`.
5. Archiver rapport qualite.

---

## 10) Checklist d'exploitation

Avant run:

- [ ] backend ERP up
- [ ] credentials API ETL valides
- [ ] DB OLAP accessible
- [ ] schemas/tables existants

Apres run:

- [ ] statut SUCCESS dans `etl_run_log.csv`
- [ ] tests qualite OK
- [ ] volumes facts non nuls
- [ ] anomalies critiques = 0

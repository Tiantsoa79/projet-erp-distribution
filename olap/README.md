# OLAP / Data Warehouse Workspace

Cette zone contient la couche decisionnelle du projet (hors `backend/`).

## Objectif

Mettre en place la partie C du sujet:

- conception d'un Data Warehouse;
- modelisation dimensionnelle (schema en etoile);
- processus ETL documente et automatise;
- base exploitable pour tableaux de bord strategiques, tactiques, operationnels.

Et respecter les contraintes de gouvernance (partie B):

- normalisation et coherence inter-modules;
- gestion des doublons/incoherences;
- separation operationnel/analytique;
- securite, fiabilite, qualite des donnees;
- preparation des donnees pour analyse.

## Structure

- `docs/`: architecture, gouvernance, dictionnaire, lineage.
- `sql/staging/`: schemas de staging (raw/clean).
- `sql/dwh/`: dimensions, faits, index/contraintes.
- `sql/quality/`: controles qualite.
- `etl/`: scripts extract/transform/load + orchestration.
- `tests/`: tests de qualite/reconciliation.
- `configs/`: configuration ETL.
- `reports/`: logs de run et rapports qualite.

## Convention de nommage

- Source OLTP: API REST du backend via gateway (`/api/v1/*`) avec authentification.
- Staging: schemas `staging_raw` et `staging_clean`.
- DWH: schema `dwh`.

## Mode d'extraction (important)

Le pipeline ETL **consomme les services REST** de l'ERP (gateway) avec login + token JWT.
Il ne lit pas directement les tables metier OLTP pour l'extract principal.

Variables requises:

- `GATEWAY_BASE_URL`
- `ETL_API_USERNAME`
- `ETL_API_PASSWORD`

Runbook operationnel complet (Windows):

- `docs/runbook-windows.md`

## Execution rapide (a completer selon environnement)

1. Creer les objets SQL dans cet ordre:
   - `sql/staging/001_create_staging.sql`
   - `sql/dwh/010_create_dimensions.sql`
   - `sql/dwh/020_create_facts.sql`
   - `sql/dwh/030_indexes_constraints.sql`
2. Configurer `configs/.env.example` -> `.env` local ETL.
3. Demarrer le backend ERP (gateway + services).
4. Lancer le pipeline:

```powershell
python olap/etl/orchestration/run_pipeline.py
```

5. Verifier:
   - `reports/etl_run_log.csv`
   - `reports/data_quality_report.md`
   - tests sous `olap/tests/`

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

## Installation et Configuration

### Prérequis
- Python 3.14+
- PostgreSQL 16+
- Node.js (pour le backend)

### Installation pour un nouveau développeur

1. **Cloner le projet**
   ```bash
   git clone <url>
   cd projet-erp-distribution
   ```

2. **Configurer le Backend** (dans `backend/`)
   ```bash
   cd backend
   copy .env.example .env
   # Éditer .env avec vos configurations
   npm install
   npm start
   ```

3. **Configurer OLAP**
   ```bash
   cd ..  # Retour à la racine
   
   # Créer l'environnement virtuel Python
   python -m venv olap/venv
   
   # Activer le venv (OBLIGATOIRE pour chaque session)
   # Windows:
   olap/venv/Scripts/activate
   # Linux/Mac:
   source olap/venv/bin/activate
   
   # Installer les dépendances
   pip install -r olap/requirements.txt
   
   # Configurer l'environnement
   copy olap/configs/.env.example olap/configs/.env
   # Éditer .env avec vos configurations (DB, API, etc.)
   ```

4. **Créer les schémas SQL**
   ```bash
   # PostgreSQL doit être lancé avec l'utilisateur postgres
   psql -U postgres -d erp_distribution -f olap/sql/staging/001_create_staging.sql
   psql -U postgres -d erp_distribution -f olap/sql/dwh/010_create_dimensions.sql
   psql -U postgres -d erp_distribution -f olap/sql/dwh/020_create_facts.sql
   psql -U postgres -d erp_distribution -f olap/sql/dwh/030_indexes_constraints.sql
   ```

## Execution

### Lancement complet

1. **Démarrer PostgreSQL**
2. **Démarrer le Backend ERP** (dans un terminal)
   ```bash
   cd backend
   npm start
   ```

3. **Lancer le pipeline OLAP** (dans un autre terminal)
   ```bash
   # À CHAQUE SESSION : activer le venv
   olap/venv/Scripts/activate
   
   # Lancer le pipeline
   python olap/etl/orchestration/run_pipeline.py
   ```

### Points importants

- **Le venv doit être activé à chaque session** pour OLAP
- Le backend doit être lancé **avant** le pipeline OLAP
- Les fichiers `.env` ne sont pas versionnés (configurations locales)
- PostgreSQL doit utiliser l'utilisateur `postgres` avec mot de passe `mdp` (par défaut)

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

## Résultats attendus

Après exécution réussie, le pipeline traite:
- **Extraction**: 793 clients, 50 fournisseurs, 1861 produits, 4922 commandes, 9800 lignes de commande, 24610 historiques de statut
- **Normalisation**: Nettoyage et standardisation des données
- **Déduplication**: 0 doublons clients, 1 doublon produit détecté
- **Chargement**: Dimensions et faits dans le Data Warehouse

## Dépannage

### Erreurs communes

1. **ModuleNotFoundError: No module named 'dotenv'**
   ```bash
   # Solution: activer le venv
   olap/venv/Scripts/activate
   ```

2. **ERREUR: le schéma « staging_raw » n'existe pas**
   ```bash
   # Solution: créer les schémas SQL
   psql -U postgres -d erp_distribution -f olap/sql/staging/001_create_staging.sql
   ```

3. **ERREUR: authentication par mot de passe échouée**
   ```bash
   # Solution: vérifier le mot de passe PostgreSQL dans .env
   # Par défaut: mdp
   ```

4. **ETL_API_USERNAME and ETL_API_PASSWORD are required**
   ```bash
   # Solution: configurer olap/configs/.env
   # Utiliser les mêmes identifiants que le backend
   ```

# Architecture OLAP et ETL

## 1. Positionnement dans le systeme global

Le systeme complet combine:

- ERP/SOA (operationnel, temps reel): `backend/`;
- OLAP/Data Warehouse (decisionnel, historise): `olap/`.

Le backend reste la source transactionnelle (OLTP). L'OLAP est construit en couche separee.

## 2. Flux de donnees

1. Extract depuis les APIs REST du backend ERP via gateway (`/api/v1/*`) avec authentification JWT.
2. Chargement brut en `staging_raw`.
3. Normalisation/controle en `staging_clean`.
4. Conformation dimensionnelle (surrogate keys + SCD2 selectif).
5. Chargement des faits dans `dwh`.
6. Reconciliation source vs DWH + rapport qualite.

## 3. Choix de modelisation

Choix principal: **schema en etoile**.

Raisons:

- performant pour agrégations BI;
- plus simple a maintenir qu'un flocon complet;
- adapte au contexte ERP distribution.

## 4. Grains analytiques

- `fact_sales_order_line`: 1 ligne de commande.
- `fact_order_status_transition`: 1 changement de statut.
- `fact_inventory_snapshot`: 1 produit x date snapshot.

## 5. Dimensions

- `dim_date`
- `dim_customer` (SCD2)
- `dim_product` (SCD2)
- `dim_supplier` (SCD2)
- `dim_geography`
- `dim_order_status`
- `dim_ship_mode`
- `dim_user`

## 6. Separation OLTP / OLAP

- schemas dedies (`staging_*`, `dwh`);
- authentification ETL via compte applicatif (`ETL_API_USERNAME` / `ETL_API_PASSWORD`);
- aucune logique analytique dans les services transactionnels.

## 7. Exigences couvertes

Partie C:

- DWH concu;
- modelisation dimensionnelle en etoile;
- ETL documente et automatisable;
- socle pour reporting strategique/tactique/operationnel.

Partie B:

- normalisation, dedoublonnage, controle d'incoherences;
- separation operationnel/analytique;
- qualite/fiabilite/audit ETL.

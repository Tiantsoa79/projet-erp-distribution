# Regles de gouvernance et qualite des donnees

## 1. Normalisation et coherence inter-modules

- IDs etrangers verifies entre domains (customer, product, supplier).
- Dates au format ISO `YYYY-MM-DD`.
- Valeurs textuelles normalisees (trim, lower pour matching technique).

## 2. Gestion des doublons et incoherences

- Doublons clients: meme `(customer_name_normalized, email_normalized)`.
- Doublons produits: meme `(product_name_normalized, supplier_id)`.
- Doublons fournisseurs: meme `(supplier_name_normalized, contact_email_normalized)`.
- Incoherences critiques:
  - `ship_date < order_date`;
  - quantite <= 0;
  - montants negatifs;
  - transition de statut invalide.

## 3. Separation donnees operationnelles / analytiques

- Source transactionnelle conservee dans `backend` (OLTP).
- Couches analytiques dans `olap` (`staging_raw`, `staging_clean`, `dwh`).
- Interdiction des ecritures ETL dans les tables OLTP metier.

## 4. Securite et fiabilite

- Compte ETL en lecture seule sur OLTP.
- Journalisation des runs ETL (`reports/etl_run_log.csv`).
- Gestion des erreurs avec statut par etape (extract/transform/load).

## 5. Preparation pour l'analyse

- Dimensions conformes avec surrogate keys.
- Historisation SCD2 pour dimensions lentes (customer/product/supplier).
- Faits au grain stable et explicite.

## 6. Controles minimum obligatoires

- Taux de nulls sur colonnes critiques.
- Comptage source vs destination.
- Detection des cles orphelines.
- Verification des bornes metier (discount, rating, lead_time, etc.).

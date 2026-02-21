# Gouvernance des données - ETL / Data Warehouse

Ce document décrit les règles de gouvernance appliquées par le pipeline ETL,
en réponse aux exigences de la Partie B du projet.

## 1. Normalisation et cohérence inter-modules

### Problème
Les données proviennent de 4 services ERP indépendants (Sales, Catalog, Customers, Suppliers).
Chaque service peut avoir des conventions d'écriture différentes (casse, espaces, formats).

### Règles appliquées

| Règle | Champs concernés | Implémentation |
|---|---|---|
| Trim + lowercase | noms clients, noms fournisseurs, noms produits, emails | `lower(trim(...))` dans `transform.py` |
| Version la plus récente | toutes les entités | `DISTINCT ON (pk) ORDER BY updated_at DESC` |
| Full-refresh staging | staging_clean.* | `TRUNCATE` avant chaque insertion |

### Justification
La normalisation garantit que les jointures dimensionnelles fonctionnent correctement
même si les services source encodent différemment les mêmes entités.
Le full-refresh élimine tout résidu de runs précédents.

## 2. Gestion des doublons et incohérences

### Doublons détectés

| Type | Critère de détection | Action |
|---|---|---|
| Clients en double | même `(customer_name_normalized, email_normalized)` | Signalé (compteur dans les logs) |
| Produits en double | même `(product_name_normalized, supplier_id)` | Signalé (compteur dans les logs) |

### Incohérences supprimées

| Type | Critère | Action |
|---|---|---|
| Dates invalides | `ship_date < order_date` | Suppression de la commande du staging clean |

### Justification
Les doublons sont détectés pour visibilité mais non supprimés automatiquement
(ils peuvent représenter des entités légitimement distinctes côté OLTP).
Les incohérences de dates sont supprimées car elles fausseraient les analyses temporelles.

## 3. Séparation OLTP / OLAP

| Aspect | Implémentation |
|---|---|
| Bases séparées | `erp_distribution` (OLTP) ≠ `erp_distribution_dwh` (DWH) |
| Pas de lecture directe | L'ETL consomme uniquement les APIs REST, jamais la base OLTP |
| Authentification | Login JWT via gateway avec compte dédié ETL |
| Schemas isolés | `staging_raw`, `staging_clean`, `dwh` dans la base DWH |

### Justification
Cette séparation garantit que :
- les charges analytiques n'impactent pas les performances transactionnelles,
- le contrat d'interface est l'API REST (pas le schéma SQL interne),
- la sécurité est gérée par le RBAC du gateway.

## 4. Traçabilité ETL

| Mécanisme | Description |
|---|---|
| `etl_run_id` | Identifiant unique par exécution (format `run_YYYYMMDD_HHMMSS`) |
| `etl_loaded_at` | Timestamp d'insertion dans chaque table staging et fait |
| Logs console | Chaque étape affiche son état et ses compteurs |

### Justification
Permet de tracer quelle exécution a produit quelles données,
et de diagnostiquer les problèmes en cas d'anomalie.

## 5. Idempotence et fiabilité

| Mécanisme | Scope | Description |
|---|---|---|
| `TRUNCATE` | staging_raw, staging_clean | Full-refresh à chaque run |
| `ON CONFLICT DO UPDATE` | faits DWH | Upsert idempotent, pas de doublons |
| `ON CONFLICT DO NOTHING` | dimensions ref | Insertion uniquement si absent |
| `IF NOT EXISTS` | DDL schema.sql | Création des objets idempotente |
| Auto-create DB | run_pipeline.py | Crée la base DWH si inexistante |

### Justification
Le pipeline peut être relancé à tout moment sans corrompre les données.
C'est essentiel pour un processus ETL automatisé en production.

## 6. Préparation pour l'analyse

Le Data Warehouse est conçu pour supporter les futurs tableaux de bord :

| Niveau | Exemples de questions | Tables de faits utilisées |
|---|---|---|
| **Stratégique** | CA par trimestre, marge globale, tendances annuelles | `fact_sales_order_line` |
| **Tactique** | Performance par catégorie produit, par segment client, par région | `fact_sales_order_line` + dimensions |
| **Opérationnel** | Délais de traitement commandes, stock critique, transitions de statut | `fact_order_status_transition`, `fact_inventory_snapshot` |

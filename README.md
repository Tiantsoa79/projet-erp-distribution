# Projet ERP Distribution

Ce repository implemente un systeme d'information integre avec deux couches complementaires:

- une couche **operationnelle ERP (OLTP)** exposee en services (`backend/`),
- une couche **decisionnelle BI/OLAP** pour ETL et Data Warehouse (`olap/`).

L'objectif suit le cadre general du sujet: ERP + SOA + BI/Data Mining + IA (progressivement).

## 1) Contexte fonctionnel global

Le projet couvre:

- **ERP**: gestion des operations metier (commandes, produits, fournisseurs, clients, utilisateurs, roles, permissions).
- **SOA**: services metier decouples exposes via API REST avec gateway.
- **BI/OLAP**: preparation decisionnelle via ETL et modele dimensionnel.
- **Data Mining / IA**: couches futures appuyees sur le Data Warehouse.

## 2) Architecture du repository

- `backend/`: ERP transactionnel (OLTP) et exposition API (SOA).
- `olap/`: ETL, staging, Data Warehouse dimensionnel et controles qualite.
- `data/`: jeux CSV sources (historique/prototypage).

## 3) Ce que represente `backend/` (ERP + OLTP)

`backend/` est le noyau transactionnel du systeme:

- operations CRUD metier,
- workflows de statuts,
- controle RBAC (users/roles/permissions),
- auditabilite et tracabilite,
- contraintes metier et temporelles.

Cette couche sert de **source operationnelle** pour l'OLAP.

Voir: `backend/README.md`.

## 4) Ce que represente `olap/` (partie decisionnelle)

`olap/` couvre la mise en place de la partie C (obligatoire):

- conception du Data Warehouse,
- modelisation dimensionnelle (schema en etoile),
- ETL documente et automatisable,
- preparation des donnees pour tableaux de bord strategiques/tactiques/operationnels.

`olap/` applique aussi les contraintes de gouvernance (partie B):

- normalisation et coherence inter-modules,
- gestion des doublons et incoherences,
- separation operationnel / analytique,
- securite, fiabilite et qualite,
- preparation des donnees pour l'analyse.

Voir: `olap/README.md`.

## 5) Point d'entree developpeur

1. Lire `backend/README.md` pour comprendre le socle ERP/OLTP.
2. Lire `olap/README.md` puis `olap/docs/architecture-olap.md` pour la couche OLAP.

## 6) Notes Git

- Les fichiers `.env` sont ignores.
- Seuls les exemples (`.env.example`) sont versionnes.

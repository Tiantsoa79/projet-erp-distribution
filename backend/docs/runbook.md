# Runbook d'exploitation locale

## 1. Prérequis

- Node.js >= 18
- PostgreSQL local accessible
- Variables d'environnement configurées (`backend/.env`)

## 2. Installation

```bash
npm install
```

## 3. Initialisation de la base

Exécuter le schéma SQL, puis importer les données:

```bash
npm run db:import
```

## 4. Démarrage des services

Démarrage simultané:

```bash
npm run start:all
```

Ou service par service:

```bash
npm run gateway:start
npm run sales:start
npm run catalog:start
npm run customers:start
npm run suppliers:start
```

## 5. Ports par défaut

- Gateway: 4000
- Sales: 4001
- Catalog: 4002
- Customers: 4003
- Suppliers: 4004

## 6. Vérifications rapides

- Health gateway: `GET /health`
- Login: `POST /api/v1/auth/login`
- Profil: `GET /api/v1/auth/me`

## 7. Dépannage fréquent

### 7.1 Erreur DB connection

- vérifier `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
- vérifier que PostgreSQL est démarré

### 7.2 401/403 en API

- token manquant/expiré/invalide
- permission absente sur le rôle utilisateur

### 7.3 409 sur commandes

- période comptable fermée (`PERIOD_CLOSED`)
- contrainte DB (doublon clé, FK invalide)

### 7.4 422 validation métier

- payload invalide (date, lignes, statuts, règles métier)

## 8. Logs et traçabilité

- `x-request-id` généré par gateway
- champs actor/request/service persistés dans `audit_logs`
- endpoint de consultation: `GET /api/v1/audit/logs`

# Projet ERP Distribution

Ce repository contient le projet ERP Distribution.

## Objectif actuel

Construire un backend multi-services en JavaScript, alimente par des donnees CSV migrees vers PostgreSQL, puis expose via une API Gateway.

## Etat actuel

- Backend Node.js operationnel (services `sales`, `catalog`, `suppliers`, `customers`)
- API Gateway operationnelle avec auth simple JWT + cookie
- Import CSV -> PostgreSQL en place (`backend/scripts/import-csv.js`)
- Documentation OpenAPI statique disponible (`backend/docs/swagger/openapi.yml`)

## Structure (pour le moment)

- `backend/` : code backend complet (services, scripts, docs)
- `data/` : jeux de donnees CSV sources

## Point d'entree pour les developpeurs

Commencer par lire:

- `backend/README.md`

Ce guide explique:
- installation,
- configuration `.env`,
- import de donnees,
- lancement des services,
- tests Postman (gateway),
- health checks directs des microservices.

## Notes Git

- Les fichiers `.env` sont ignores.
- Seuls les fichiers d'exemple (`.env.example`) sont versionnes.

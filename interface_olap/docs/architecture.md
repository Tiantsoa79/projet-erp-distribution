# Architecture de l'Interface OLAP

## Vue d'ensemble

L'interface OLAP est une application web JavaScript moderne qui expose les tableaux de bord du Data Warehouse ERP Distribution. Elle adopte une architecture client/serveur simple sans build step.

## Stack technique

### Backend (Node.js)
- **Framework** : Express.js 4.21.0
- **Base de données** : PostgreSQL via `pg` (pool de connexions)
- **Authentification** : Aucune (accès local uniquement)

### Frontend (Vanilla JS)
- **Routing** : SPA hash-based (`#/page`)
- **Graphiques** : Chart.js 4.4.4 (CDN)
- **Styles** : CSS custom moderne (variables CSS, grid/flexbox)
- **Pas de build step** : fichiers statiques servis directement

## Structure des fichiers

```
interface_olap/
├── server.js              # Serveur Express principal
├── db.js                   # Pool PostgreSQL
├── routes/
│   ├── dashboard.js        # Endpoints API pour les dashboards
│   └── pipeline.js         # Endpoint pour lancer l'ETL
├── public/
│   ├── index.html          # Shell SPA
│   ├── css/style.css       # Styles complets
│   └── js/
│       ├── app.js          # Routeur SPA
│       ├── api.js          # Client HTTP
│       ├── charts.js       # Helpers Chart.js
│       └── pages/          # Pages des dashboards
└── docs/                   # Documentation
```

## Flux de données

```
PostgreSQL DWH ←→ API Express ←→ Frontend JS
     ↑                      ↑
  Requêtes SQL          Appels fetch()
     ↓                      ↓
  Données JSON         Graphiques Chart.js
```

## Endpoints API

### Dashboard
- `GET /api/dashboard/strategic` - KPIs et données stratégiques
- `GET /api/dashboard/tactical` - Données tactiques  
- `GET /api/dashboard/operational` - Données opérationnelles

### Pipeline
- `POST /api/pipeline/run` - Lancer le pipeline ETL
- `GET /api/pipeline/status` - Statut et logs en temps réel

## Sécurité

L'interface est conçue pour un usage local en entreprise :
- Pas d'exposition publique
- Connexion directe à PostgreSQL DWH
- Pas de gestion de sessions utilisateurs

## Performance

- **Connexions DB** : Pool de 10 connexions max
- **Cache client** : Aucun (rafraîchissement manuel)
- **Temps de réponse** : < 500ms pour les requêtes dashboard typiques

## Évolution possible

- Ajout d'authentification (JWT)
- Cache Redis pour les requêtes fréquentes
- WebSocket pour les mises à jour temps réel
- Export PDF/PNG des graphiques

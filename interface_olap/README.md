# Interface OLAP - Tableaux de bord BI

Interface web JavaScript pour visualiser les tableaux de bord BI du Data Warehouse ERP Distribution.

## Structure

```
interface_olap/
├── package.json
├── .env.example              # Configuration (copier vers .env)
├── server.js                 # Serveur Express (API + fichiers statiques)
├── db.js                     # Pool de connexion PostgreSQL
├── routes/
│   ├── dashboard.js          # Endpoints API : /strategic, /tactical, /operational
│   └── pipeline.js           # Endpoint API : lancer le pipeline ETL
└── public/
    ├── index.html            # SPA shell
    ├── css/
    │   └── style.css         # Styles (sidebar, cards, charts, tables)
    └── js/
        ├── app.js            # Routeur SPA (hash-based)
        ├── api.js            # Client API
        ├── charts.js         # Helpers Chart.js
        └── pages/
            ├── pipeline.js   # Page Pipeline ETL
            ├── strategic.js  # Dashboard Strategique
            ├── tactical.js   # Dashboard Tactique
            └── operational.js# Dashboard Operationnel
```

## Pages

| Route | Dashboard | Public cible | Contenu |
|---|---|---|---|
| `#/` | Pipeline ETL | Administrateur | Bouton lancer ETL (normal + force), logs temps reel |
| `#/strategic` | Strategique | Direction | KPIs, CA mensuel, segments, geo, top produits |
| `#/tactical` | Tactique | Managers | Tendance quotidienne, categories, statuts, modes livraison |
| `#/operational` | Operationnel | Equipes | Commandes recentes, alertes stock, transitions, geo |

## Installation

```powershell
cd interface_olap
copy .env.example .env
# Editer .env avec vos identifiants PostgreSQL
npm install
```

## Lancement

```powershell
npm start
```

Ouvrir `http://localhost:3030` dans le navigateur.

## Prerequis

- Node.js 18+
- PostgreSQL local avec la base DWH peuplee
- Le pipeline ETL (`python BI/run_pipeline.py`) doit avoir ete execute au moins une fois
- Le backend ERP n'a PAS besoin d'etre demarre pour consulter les dashboards

## Documentation

- **[README](docs/README.md)** - Vue d'ensemble et démarrage rapide
- **[Architecture](docs/architecture.md)** - Stack technique et structure
- **[Runbook](docs/runbook.md)** - Guide d'exploitation complet
- **[API Reference](docs/api.md)** - Documentation des endpoints REST

## Technologies

- **Backend** : Express.js, pg (PostgreSQL client)
- **Frontend** : Vanilla JS (SPA), Chart.js 4, CSS custom
- **Pas de build step** : tout est servi en fichiers statiques

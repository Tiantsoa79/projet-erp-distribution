# Interface OLAP - Documentation

Bienvenue dans la documentation de l'interface OLAP, le portail web des tableaux de bord Business Intelligence pour l'ERP Distribution.

## 📋 Sommaire

- [Architecture](architecture.md) - Vue d'ensemble technique de l'application
- [Runbook](runbook.md) - Guide d'exploitation pas à pas
- [API Reference](api.md) - Documentation des endpoints REST

## 🚀 Démarrage rapide

```powershell
cd interface_olap
npm install
npm start
```

Ouvrir `http://localhost:3030` dans votre navigateur.

## 📊 Tableaux de bord disponibles

| Dashboard | Public cible | Description |
|-----------|--------------|-------------|
| **Stratégique** | Direction générale | KPIs globaux, tendances, performance par segment/région |
| **Tactique** | Managers | Analyses quotidiennes, catégories produits, statuts commandes |
| **Opérationnel** | Équipes | Commandes récentes, alertes stock, transitions statut |

## 🔧 Prérequis

- Node.js 18+
- PostgreSQL local avec base DWH peuplée
- Pipeline ETL exécuté au moins une fois (`python ../BI/run_pipeline.py`)

## 📞 Support

En cas de problème, consultez le [runbook](runbook.md) pour le dépannage pas à pas.

# Data Mining - Documentation

Bienvenue dans la documentation du module Data Mining pour l'ERP Distribution.

## 📋 Sommaire

- [Architecture](architecture.md) - Vue d'ensemble technique et structure
- [Runbook](runbook.md) - Guide d'exploitation pas à pas
- [API Reference](api.md) - Documentation des endpoints REST

## 🚀 Démarrage rapide

```powershell
cd data_mining
python run_mining.py
```

## 📊 Analyses disponibles

| Analyse | Description | Méthode |
|---------|-------------|---------|
| **Exploratoire** | Statistiques descriptives, corrélations, patterns | Analyse univariée/bivariée |
| **Clustering** | Segmentation clients comportementale | K-Means |
| **Anomalies** | Détection transactions suspectes | Isolation Forest |
| **RFM** | Segmentation Récence-Fréquence-Montant | Analyse RFM |

## 🔧 Prérequis

- Python 3.8+
- PostgreSQL avec base DWH peuplée
- Dépendances Python (voir requirements.txt)

## 📞 Support

En cas de problème, consultez le [runbook](runbook.md) pour le dépannage pas à pas.

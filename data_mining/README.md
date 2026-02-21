# Data Mining - ERP Distribution

Module de Data Mining pour l'analyse avancee des donnees du Data Warehouse ERP.

## Techniques implementees

- **Analyse exploratoire** : statistiques descriptives, visualisations, correlations
- **Segmentation clients** : clustering K-Means pour identifier les profils clients
- **Detection d'anomalies** : Isolation Forest pour identifier les transactions suspectes
- **Analyse RFM** : Recence, Frequence, Montant pour segmenter la clientele

## Demarrage rapide

```powershell
# Toutes les analyses
python data_mining/run_mining.py

# Analyse specifique
python data_mining/run_mining.py --analysis clustering
python data_mining/run_mining.py --analysis rfm

# Mode rapide (echantillon)
python data_mining/run_mining.py --quick
```

## Prerequis

- Python 3.10+
- PostgreSQL avec base DWH peuplee (pipeline ETL execute)
- Dependances Python : `pip install -r data_mining/requirements.txt`
- Configuration : `.env` a la racine du projet (section DATA MINING)

## Resultats

Les analyses sont sauvegardees dans `results/` :
- `plots/` : graphiques et visualisations (PNG)
- `reports/` : rapports HTML detailles
- `data/` : donnees exportees (CSV)

## Documentation

- [Architecture](docs/architecture.md) - Vue d'ensemble technique
- [Runbook](docs/runbook.md) - Guide d'exploitation
- [API Reference](docs/api.md) - Endpoints pour l'integration web

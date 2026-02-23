# Automatisation Quotidienne Simplifiée

## Vue d'ensemble

Version simplifiée pour un usage quotidien avec exécution toutes les 24h.

## Usage

### Exécution immédiate
```bash
python daily_automation.py
```

### Planification automatique (toutes les 24h)
```bash
python daily_automation.py --schedule
```

## Ce que ça fait

1. **Vérification des changements** : Lance l'ETL et détecte s'il y a des nouvelles données
2. **Data Mining** : Si changements détectés, exécute les analyses avancées
3. **AI Reporting** : Si Data Mining réussi, génère les insights et recommandations

## Avantages

- ✅ **Simple** : Un seul script à lancer
- ✅ **Efficace** : Exécute les analyses seulement si nécessaire
- ✅ **Automatique** : Planification toutes les 24h
- ✅ **Léger** : Pas de monitoring complexe inutile

## Logs

- `daily_automation.log` : Journal des exécutions
- Affichage console en temps réel

## Idéal pour

- Usage quotidien avec peu de changements
- Exécution nocturne automatique (2h du matin)
- Environnements de production stables

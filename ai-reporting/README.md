# AI Reporting - ERP Distribution

Reporting assiste par l'Intelligence Artificielle.

## Fonctionnalites

- **Generation automatique d'insights** : analyse statistique + enrichissement IA
- **Interpretation des indicateurs** : KPIs commentes et contextualises
- **Recommandations decisionnelles** : actions priorisees basees sur les donnees
- **Data storytelling** : narration automatique des resultats

## Mode de fonctionnement

| Mode | Description | Prerequis |
|------|-------------|-----------|
| **Statistique** | Insights et recommandations bases sur des regles | Aucune cle API |
| **IA (OpenAI)** | Analyses enrichies par GPT-4 | `OPENAI_API_KEY` |
| **IA (Claude)** | Analyses enrichies par Claude | `CLAUDE_API_KEY` |
| **IA (Gemini)** | Analyses enrichies par Gemini (GRATUIT) | `GEMINI_API_KEY` |
| **IA (Local)** | LLM local via Ollama | Ollama en cours d'execution |

Le module fonctionne **toujours**, meme sans cle API (mode fallback statistique).

## Usage

```bash
# Rapport complet (IA si disponible, sinon statistique)
python ai-reporting/run_reporting.py

# Mode statistique uniquement
python ai-reporting/run_reporting.py --no-ai

# Sortie JSON (pour l'interface web)
python ai-reporting/run_reporting.py --json
```

## Structure

```
ai-reporting/
  run_reporting.py       # Point d'entree (orchestrateur)
  llm_client.py          # Client LLM multi-provider
  data_collector.py      # Collecte donnees DWH
  insight_generator.py   # Generation d'insights
  recommendations.py     # Recommandations decisionnelles
  storytelling.py        # Data storytelling
  results/               # Rapports generes (JSON)
```

## Configuration

Variables dans le `.env` racine (section AI REPORTING) :

```
AI_PROVIDER=gemini          # openai | claude | gemini | local
OPENAI_API_KEY=sk-...       # Cle API OpenAI (optionnel)
CLAUDE_API_KEY=sk-ant-...   # Cle API Claude (optionnel)
GEMINI_API_KEY=AIza...      # Cle API Gemini (optionnel, GRATUIT)
```

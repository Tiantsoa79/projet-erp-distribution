#!/usr/bin/env python3
"""
Pipeline AI Reporting - ERP Distribution

Genere un rapport intelligent assiste par IA :
  - Insights automatiques (statistiques + IA)
  - Recommandations decisionnelles
  - Data storytelling (narration automatique)

Usage :
    python ai-reporting/run_reporting.py              # rapport complet
    python ai-reporting/run_reporting.py --no-ai      # mode statistique uniquement
    python ai-reporting/run_reporting.py --json        # sortie JSON (pour l'interface)

Fonctionne sans cle API (mode fallback statistique).
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Resoudre les chemins
REPORTING_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = REPORTING_DIR.parent
sys.path.insert(0, str(REPORTING_DIR))

# Charger .env racine en priorite
_env = PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else REPORTING_DIR / ".env"
load_dotenv(_env)

from llm_client import LLMClient
from data_collector import collect_business_context
from insight_generator import generate_insights
from recommendations import generate_recommendations
from storytelling import generate_story


def ensure_results_dir():
    results = REPORTING_DIR / "results"
    results.mkdir(exist_ok=True)
    return results


def print_header():
    print("=" * 70)
    print("  AI REPORTING  |  ERP Distribution")
    print("=" * 70)
    print(f"Debut : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def print_ai_status(llm: LLMClient):
    status = llm.get_status()
    if status["ai_available"]:
        print(f"[OK] IA disponible (provider: {status['active_provider']})")
    else:
        print("[INFO] IA non configuree - mode statistique (fallback)")
        print("       Configurez OPENAI_API_KEY ou CLAUDE_API_KEY dans .env pour activer l'IA")
    print()


def run_reporting(no_ai=False, output_json=False):
    """Execute le pipeline de reporting."""
    print_header()

    # 1. Initialiser le client LLM
    llm = LLMClient()
    if no_ai:
        llm.providers = {}  # Desactive tous les providers
    print_ai_status(llm)

    # 2. Collecter le contexte business
    print("--- 1. Collecte des donnees business ---")
    try:
        context = collect_business_context()
        kpis = context.get("kpis", {})
        print(f"[OK] Donnees collectees : {kpis.get('commandes', 0):,} commandes, "
              f"{kpis.get('clients', 0):,} clients")
    except Exception as exc:
        print(f"[ERREUR] Impossible de collecter les donnees : {exc}")
        return 1

    # 3. Generer les insights
    print("\n--- 2. Generation des insights ---")
    try:
        insights = generate_insights(context, llm)
        n_insights = len(insights.get("statistical", []))
        mode = insights["mode"]
        print(f"[OK] {n_insights} insights generes (mode: {mode})")
    except Exception as exc:
        print(f"[ERREUR] Erreur generation insights : {exc}")
        insights = {"mode": "error", "statistical": [], "ai_analysis": None}

    # 4. Generer les recommandations
    print("\n--- 3. Generation des recommandations ---")
    try:
        recs = generate_recommendations(context, llm)
        n_recs = len(recs.get("statistical", []))
        print(f"[OK] {n_recs} recommandations generees (mode: {recs['mode']})")
    except Exception as exc:
        print(f"[ERREUR] Erreur generation recommandations : {exc}")
        recs = {"mode": "error", "statistical": [], "ai_recommendations": None}

    # 5. Data storytelling
    print("\n--- 4. Data Storytelling ---")
    try:
        story = generate_story(context, llm)
        print(f"[OK] Narration generee (mode: {story['mode']})")
    except Exception as exc:
        print(f"[ERREUR] Erreur storytelling : {exc}")
        story = {"mode": "error", "statistical_story": "", "ai_story": None}

    # 6. Assembler le rapport
    report = {
        "timestamp": datetime.now().isoformat(),
        "ai_available": llm.is_available() and not no_ai,
        "ai_provider": llm.provider if llm.is_available() and not no_ai else None,
        "kpis": context.get("kpis", {}),
        "insights": insights,
        "recommendations": recs,
        "storytelling": story,
    }

    # 7. Sauvegarder
    results_dir = ensure_results_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = results_dir / f"ai_report_{ts}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False),
                           encoding="utf-8")

    if output_json:
        print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
    else:
        _print_report(report)

    print(f"\n[OK] Rapport sauvegarde : {report_path}")
    print(f"Termine : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


def _print_report(report: dict):
    """Affiche le rapport en mode texte."""
    print("\n" + "=" * 70)
    print("  RAPPORT AI REPORTING")
    print("=" * 70)

    # Storytelling
    story = report.get("storytelling", {})
    if story.get("ai_story"):
        print("\n" + story["ai_story"])
    elif story.get("statistical_story"):
        print("\n" + story["statistical_story"])

    # Insights
    insights = report.get("insights", {})
    if insights.get("ai_analysis"):
        print("\n--- Analyse IA ---")
        print(insights["ai_analysis"])

    # Recommandations
    recs = report.get("recommendations", {})
    stat_recs = recs.get("statistical", [])
    if stat_recs:
        print("\n--- Recommandations ---")
        for i, r in enumerate(stat_recs, 1):
            print(f"\n  {i}. [{r['priorite'].upper()}] {r['domaine']}")
            print(f"     {r['recommandation']}")
            print(f"     Impact : {r['impact_estime']}")

    if recs.get("ai_recommendations"):
        print("\n--- Recommandations IA ---")
        print(recs["ai_recommendations"])


def main():
    parser = argparse.ArgumentParser(description="AI Reporting - ERP Distribution")
    parser.add_argument("--no-ai", action="store_true",
                        help="Mode statistique uniquement (sans LLM)")
    parser.add_argument("--json", action="store_true",
                        help="Sortie JSON (pour integration interface)")
    args = parser.parse_args()

    return run_reporting(no_ai=args.no_ai, output_json=args.json)


if __name__ == "__main__":
    sys.exit(main())

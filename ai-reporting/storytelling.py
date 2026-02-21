"""
Data Storytelling - Narration automatique des resultats.

Genere un recit structure a partir des donnees DWH,
soit enrichi par IA, soit en mode statistique pur.
"""

import json
from datetime import datetime
from typing import Dict, List

from llm_client import LLMClient


SYSTEM_PROMPT = """Tu es un expert en data storytelling pour une entreprise de distribution.
Tu rediges des narrations professionnelles, engageantes et basees sur les donnees.
Structure ton recit avec introduction, constats cles, analyse et conclusion.
Reponds en francais."""


def generate_story(context: Dict, llm: LLMClient) -> Dict:
    """Genere une narration basee sur les donnees."""
    statistical_story = _build_statistical_story(context)

    if llm.is_available():
        ai_story = _build_ai_story(context, llm)
        return {"mode": "ai", "statistical_story": statistical_story, "ai_story": ai_story}

    return {"mode": "statistical", "statistical_story": statistical_story, "ai_story": None}


# ------------------------------------------------------------------
# Narration statistique (fallback)
# ------------------------------------------------------------------

def _build_statistical_story(ctx: Dict) -> str:
    """Construit une narration structuree sans IA."""
    kpis = ctx.get("kpis", {})
    trend = ctx.get("monthly_trend", [])
    products = ctx.get("top_products", [])
    segments = ctx.get("segments", [])
    alerts = ctx.get("stock_alerts", [])
    geo = ctx.get("geo_performance", [])

    parts = []

    # Titre
    parts.append(f"RAPPORT BUSINESS - {datetime.now().strftime('%d/%m/%Y')}")
    parts.append("=" * 50)

    # Introduction
    parts.append("\n## Vue d'ensemble\n")
    parts.append(
        f"L'activite de l'entreprise affiche un chiffre d'affaires total de "
        f"{kpis.get('ca_total', 0):,.0f} EUR, genere par {kpis.get('commandes', 0):,} "
        f"commandes aupres de {kpis.get('clients', 0):,} clients. "
        f"La marge globale s'etablit a {kpis.get('marge_pct', 0):.1f}%, "
        f"pour un profit cumule de {kpis.get('profit_total', 0):,.0f} EUR."
    )

    # Tendance
    if len(trend) >= 2:
        parts.append("\n## Dynamique commerciale\n")
        last = trend[-1]
        prev = trend[-2]
        delta = ((last["ca"] - prev["ca"]) / prev["ca"] * 100) if prev["ca"] else 0
        direction = "progression" if delta > 0 else "recul"
        parts.append(
            f"Sur le dernier mois ({last['mois']}), le CA atteint {last['ca']:,.0f} EUR, "
            f"soit une {direction} de {abs(delta):.1f}% par rapport a {prev['mois']} "
            f"({prev['ca']:,.0f} EUR). "
            f"Le nombre de commandes s'eleve a {last['commandes']:,}."
        )

    # Produits
    if products:
        parts.append("\n## Produits phares\n")
        for i, p in enumerate(products[:3], 1):
            parts.append(
                f"  {i}. {p['produit']} ({p['categorie']}) : "
                f"{p['ca']:,.0f} EUR de CA, {p['quantite']:,} unites vendues."
            )

    # Segments
    if segments:
        parts.append("\n## Analyse par segment client\n")
        for s in segments:
            parts.append(
                f"  - {s['segment']} : {s['ca']:,.0f} EUR ({s['commandes']:,} commandes)"
            )

    # Geographie
    if geo:
        parts.append("\n## Performance geographique\n")
        for g in geo[:5]:
            parts.append(
                f"  - {g['region']} : {g['ca']:,.0f} EUR ({g['commandes']:,} commandes)"
            )

    # Alertes
    if alerts:
        parts.append("\n## Points d'attention\n")
        parts.append(
            f"Attention : {len(alerts)} produit(s) presentent un stock inferieur "
            f"a 10 unites et necessitent un reapprovisionnement urgent."
        )
        for a in alerts[:5]:
            parts.append(f"  - {a['produit']} : {a['stock']} unites restantes")

    # Conclusion
    parts.append("\n## Conclusion\n")
    if kpis.get("marge_pct", 0) > 20:
        parts.append("La rentabilite de l'entreprise est solide. "
                      "L'enjeu est de maintenir cette dynamique.")
    else:
        parts.append("La marge reste perfectible. Des actions sur la politique "
                      "tarifaire et l'optimisation des couts sont recommandees.")

    return "\n".join(parts)


# ------------------------------------------------------------------
# Narration IA
# ------------------------------------------------------------------

def _build_ai_story(ctx: Dict, llm: LLMClient) -> str:
    """Appelle le LLM pour generer une narration riche."""
    stat_story = _build_statistical_story(ctx)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""A partir du rapport statistique ci-dessous,
redige un recit de data storytelling professionnel et engageant.

Structure attendue :
1. Accroche (chiffre cle marquant)
2. Contexte (situation globale)
3. Constats cles (3-4 faits majeurs)
4. Analyse (cause-effet)
5. Recommandations (2-3 actions prioritaires)
6. Conclusion prospective

Rapport source :\n{stat_story}"""},
    ]
    return llm.chat(messages, temperature=0.6, max_tokens=2500)

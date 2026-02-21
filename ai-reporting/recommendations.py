"""
Generateur de recommandations decisionnelles.

Produit des recommandations actionnables basees sur les donnees DWH.
Mode IA ou mode statistique (fallback).
"""

import json
from typing import Dict, List

from llm_client import LLMClient


SYSTEM_PROMPT = """Tu es un consultant senior en strategie commerciale pour une
entreprise de distribution. Tu fournis des recommandations decisionnelles
concretes, chiffrees et priorisees. Reponds en francais."""


def generate_recommendations(context: Dict, llm: LLMClient) -> Dict:
    """Genere des recommandations basees sur le contexte business."""
    statistical = _statistical_recommendations(context)

    if llm.is_available():
        ai_recs = _ai_recommendations(context, llm)
        return {"mode": "ai", "statistical": statistical, "ai_recommendations": ai_recs}

    return {"mode": "statistical", "statistical": statistical, "ai_recommendations": None}


def _statistical_recommendations(ctx: Dict) -> List[Dict]:
    """Recommandations basees sur des regles statistiques."""
    recs = []
    kpis = ctx.get("kpis", {})
    trend = ctx.get("monthly_trend", [])
    alerts = ctx.get("stock_alerts", [])
    segments = ctx.get("segments", [])
    products = ctx.get("top_products", [])

    # Marge faible
    marge = kpis.get("marge_pct", 0)
    if marge < 15:
        recs.append({
            "priorite": "haute",
            "domaine": "Rentabilite",
            "recommandation": f"La marge globale est de {marge:.1f}%. "
                              "Revoir la politique tarifaire et negocier les couts fournisseurs.",
            "impact_estime": "Amelioration potentielle de 2-5 points de marge",
        })

    # Tendance baissiere
    if len(trend) >= 2:
        last, prev = trend[-1], trend[-2]
        delta = ((last["ca"] - prev["ca"]) / prev["ca"] * 100) if prev["ca"] else 0
        if delta < -5:
            recs.append({
                "priorite": "haute",
                "domaine": "Croissance",
                "recommandation": f"Le CA est en baisse de {abs(delta):.1f}% sur le dernier mois. "
                                  "Lancer des actions commerciales ciblees (promotions, relance clients inactifs).",
                "impact_estime": "Stabilisation du CA a court terme",
            })

    # Alertes stock
    if alerts:
        recs.append({
            "priorite": "haute",
            "domaine": "Supply Chain",
            "recommandation": f"{len(alerts)} produits en rupture imminente (stock < 10). "
                              "Passer des commandes de reapprovisionnement en urgence.",
            "impact_estime": "Eviter les ruptures et la perte de CA associee",
        })

    # Concentration client
    if segments and kpis.get("ca_total", 0) > 0:
        top_seg = segments[0]
        pct = top_seg["ca"] / kpis["ca_total"] * 100
        if pct > 50:
            recs.append({
                "priorite": "moyenne",
                "domaine": "Diversification",
                "recommandation": f"Le segment '{top_seg['segment']}' represente {pct:.0f}% du CA. "
                                  "Diversifier le portefeuille client pour reduire le risque.",
                "impact_estime": "Reduction du risque de dependance",
            })

    # Panier moyen
    panier = kpis.get("panier_moyen", 0)
    if panier > 0:
        recs.append({
            "priorite": "moyenne",
            "domaine": "Cross-selling",
            "recommandation": f"Panier moyen actuel : {panier:,.0f} EUR. "
                              "Mettre en place des strategies de cross-selling et up-selling "
                              "pour augmenter la valeur par commande.",
            "impact_estime": "Augmentation du panier moyen de 10-15%",
        })

    return recs


def _ai_recommendations(ctx: Dict, llm: LLMClient) -> str:
    """Appelle le LLM pour des recommandations enrichies."""
    kpis = ctx.get("kpis", {})
    trend = ctx.get("monthly_trend", [])
    alerts = ctx.get("stock_alerts", [])

    context_text = (
        f"KPIs: CA={kpis.get('ca_total',0):,.0f} EUR, Marge={kpis.get('marge_pct',0):.1f}%, "
        f"Commandes={kpis.get('commandes',0):,}, Clients={kpis.get('clients',0):,}\n"
    )
    if trend:
        context_text += "Tendance recente:\n"
        for t in trend[-3:]:
            context_text += f"  {t['mois']}: CA={t['ca']:,.0f}, Commandes={t['commandes']}\n"
    if alerts:
        context_text += f"\n{len(alerts)} produits en stock critique.\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""A partir de ces donnees, genere 5 recommandations
decisionnelles priorisees (haute/moyenne/basse). Pour chacune :
1. Priorite
2. Domaine (ventes, stock, clients, rentabilite, etc.)
3. Action concrete
4. Impact estime
5. Horizon temporel (court/moyen/long terme)

Donnees:\n{context_text}"""},
    ]
    return llm.chat(messages, temperature=0.4, max_tokens=2000)

"""
Generateur d'insights automatiques.

Produit des insights business a partir des donnees du DWH.
- Mode IA : utilise un LLM pour generer des analyses riches.
- Mode fallback : produit des insights statistiques purs sans LLM.
"""

import json
from typing import Dict, List

from llm_client import LLMClient
from data_collector import collect_business_context


SYSTEM_PROMPT = """Tu es un expert senior en Business Intelligence et analyse de donnees
pour une entreprise de distribution ERP. Tu produis des insights business concis,
actionnables et structures. Reponds toujours en francais."""


def generate_insights(context: Dict, llm: LLMClient) -> Dict:
    """Genere des insights a partir du contexte business.

    Si le LLM est disponible, produit des insights enrichis par l'IA.
    Sinon, produit des insights statistiques purs.
    """
    statistical = _statistical_insights(context)

    if llm.is_available():
        ai_insights = _ai_insights(context, llm)
        return {
            "mode": "ai",
            "provider": llm.provider,
            "statistical": statistical,
            "ai_analysis": ai_insights,
        }

    return {
        "mode": "statistical",
        "provider": None,
        "statistical": statistical,
        "ai_analysis": None,
    }


# ------------------------------------------------------------------
# Insights statistiques (fallback sans IA)
# ------------------------------------------------------------------

def _statistical_insights(ctx: Dict) -> List[Dict]:
    """Produit des insights purement statistiques."""
    insights = []
    kpis = ctx.get("kpis", {})
    trend = ctx.get("monthly_trend", [])
    products = ctx.get("top_products", [])
    segments = ctx.get("segments", [])
    alerts = ctx.get("stock_alerts", [])
    geo = ctx.get("geo_performance", [])

    # 1. KPI overview
    insights.append({
        "titre": "Performance globale",
        "type": "kpi",
        "description": (
            f"CA total : {kpis.get('ca_total', 0):,.0f} EUR | "
            f"Profit : {kpis.get('profit_total', 0):,.0f} EUR | "
            f"Marge : {kpis.get('marge_pct', 0):.1f}% | "
            f"{kpis.get('commandes', 0):,} commandes | "
            f"{kpis.get('clients', 0):,} clients"
        ),
        "impact": "high",
    })

    # 2. Tendance
    if len(trend) >= 2:
        last = trend[-1]
        prev = trend[-2]
        delta_pct = ((last["ca"] - prev["ca"]) / prev["ca"] * 100) if prev["ca"] else 0
        direction = "hausse" if delta_pct > 0 else "baisse"
        insights.append({
            "titre": f"Tendance mensuelle : {direction}",
            "type": "trend",
            "description": (
                f"Le CA de {last['mois']} ({last['ca']:,.0f} EUR) est en "
                f"{direction} de {abs(delta_pct):.1f}% par rapport a {prev['mois']} "
                f"({prev['ca']:,.0f} EUR)."
            ),
            "impact": "high" if abs(delta_pct) > 10 else "medium",
        })

    # 3. Concentration produits
    if products:
        top3_ca = sum(p["ca"] for p in products[:3])
        total_ca = kpis.get("ca_total", 1)
        pct = top3_ca / total_ca * 100 if total_ca else 0
        insights.append({
            "titre": "Concentration du CA sur les top produits",
            "type": "product",
            "description": (
                f"Les 3 premiers produits representent {pct:.1f}% du CA total. "
                f"Leader : {products[0]['produit']} ({products[0]['ca']:,.0f} EUR)."
            ),
            "impact": "medium",
        })

    # 4. Segments
    if segments:
        best = segments[0]
        insights.append({
            "titre": f"Segment leader : {best['segment']}",
            "type": "segment",
            "description": (
                f"Le segment '{best['segment']}' genere {best['ca']:,.0f} EUR "
                f"avec {best['commandes']:,} commandes."
            ),
            "impact": "medium",
        })

    # 5. Alertes stock
    if alerts:
        insights.append({
            "titre": f"Alerte stock : {len(alerts)} produit(s) critique(s)",
            "type": "alert",
            "description": (
                f"{len(alerts)} produits ont un stock inferieur a 10 unites. "
                f"Le plus critique : {alerts[0]['produit']} ({alerts[0]['stock']} unites)."
            ),
            "impact": "high",
        })

    # 6. Geographie
    if geo:
        top_region = geo[0]
        insights.append({
            "titre": f"Region la plus performante : {top_region['region']}",
            "type": "geo",
            "description": (
                f"{top_region['region']} : {top_region['ca']:,.0f} EUR de CA, "
                f"{top_region['commandes']:,} commandes."
            ),
            "impact": "medium",
        })

    return insights


# ------------------------------------------------------------------
# Insights enrichis par IA
# ------------------------------------------------------------------

def _ai_insights(ctx: Dict, llm: LLMClient) -> str:
    """Appelle le LLM pour generer une analyse enrichie."""
    context_text = _format_context(ctx)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Analyse ces donnees business et genere exactement 5 insights
actionnables. Pour chaque insight, fournis :
1. Un titre
2. L'observation (chiffres a l'appui)
3. L'impact business
4. Une recommandation concrete

Donnees :
{context_text}
"""},
    ]
    return llm.chat(messages, temperature=0.4, max_tokens=2000)


def _format_context(ctx: Dict) -> str:
    """Formate le contexte business en texte pour le LLM."""
    parts = []
    kpis = ctx.get("kpis", {})
    parts.append(f"KPIs: CA={kpis.get('ca_total',0):,.0f} EUR, "
                 f"Profit={kpis.get('profit_total',0):,.0f} EUR, "
                 f"Marge={kpis.get('marge_pct',0):.1f}%, "
                 f"Commandes={kpis.get('commandes',0):,}, "
                 f"Clients={kpis.get('clients',0):,}")

    trend = ctx.get("monthly_trend", [])
    if trend:
        parts.append("Tendance mensuelle (derniers mois):")
        for t in trend[-6:]:
            parts.append(f"  {t['mois']}: CA={t['ca']:,.0f}, Commandes={t['commandes']}")

    products = ctx.get("top_products", [])
    if products:
        parts.append("Top produits:")
        for p in products[:5]:
            parts.append(f"  {p['produit']} ({p['categorie']}): CA={p['ca']:,.0f}")

    segments = ctx.get("segments", [])
    if segments:
        parts.append("Segments:")
        for s in segments:
            parts.append(f"  {s['segment']}: CA={s['ca']:,.0f}, Commandes={s['commandes']}")

    alerts = ctx.get("stock_alerts", [])
    if alerts:
        parts.append(f"Alertes stock ({len(alerts)} produits < 10 unites):")
        for a in alerts[:5]:
            parts.append(f"  {a['produit']}: {a['stock']} unites")

    return "\n".join(parts)

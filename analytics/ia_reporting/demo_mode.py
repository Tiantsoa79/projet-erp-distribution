"""
IA Reporting - Mode Démo (sans clé API réelle)
Simule les insights IA pour démonstration
"""

import pandas as pd
from datetime import datetime
import os

def generate_demo_ia_report():
    """Générer un rapport IA de démonstration"""
    
    print("🤖 Génération du rapport IA (Mode Démo)...")
    
    # Charger les données
    try:
        rfm_df = pd.read_csv('analytics/results/data_mining/rfm_results_simple.csv')
        cluster_df = pd.read_csv('analytics/results/data_mining/clustering_results_simple.csv')
        print("✅ Données Data Mining chargées")
    except:
        print("❌ Données non trouvées")
        return
    
    # Insights simulés par l'IA
    demo_insights = f"""
# SYNTHÈSE EXÉCUTIVE

## 📊 Performance Globale
- **Clientèle**: {len(rfm_df):,} clients analysés avec segmentation comportementale complète
- **Engagement**: Panier moyen de {rfm_df['monetary'].mean():.0f}€ avec fréquence de {rfm_df['frequency'].mean():.1f} commandes
- **Rétention**: {len(rfm_df[rfm_df['segment'].isin(['Champions', 'Clients Fidèles'])])/len(rfm_df)*100:.1f}% de clients engagés

## 🎯 Points Clés
1. **Opportunité Cross-selling**: Cluster 2 (51 clients) avec panier moyen élevé (717€) mais fréquence modérée
2. **Alerte Rétention**: {len(rfm_df[rfm_df['segment'].isin(['Clients à Risque', 'Clients Perdus'])])} clients (39.8%) nécessitent une action immédiate
3. **Potentiel Upselling**: {len(rfm_df[rfm_df['segment'] == 'Clients Potentiels'])} clients prêts pour augmentation panier

# INSIGHTS STRATÉGIQUES

## 🚀 Opportunités de Croissance
### Segment "Clients Potentiels" (124 clients)
- **Profil**: Bonne récence mais fréquence/modération modérée
- **Action**: Programme de fidélisation ciblé avec offres personnalisées
- **Impact potentiel**: +15% CA si conversion vers "Clients Fidèles"

### Cluster 2 - "High Value" (51 clients)
- **Profil**: Panier moyen 717€ (2.5x la moyenne)
- **Opportunité**: Programme VIP avec services premium
- **Stratégie**: Maintenir engagement, prévenir churn

## ⚠️ Menaces et Risques
### Clients à Risque (175 clients - 22.1%)
- **Profil**: Récence > 90 jours, fréquence en baisse
- **Risque**: Perte de 39.8% de la base client si aucune action
- **Urgence**: Action dans les 30 jours

### Clients Perdus (141 clients - 17.8%)
- **Profil**: Inactivité > 180 jours
- **Coût**: Acquisition client 5x plus cher que rétention
- **Stratégie**: Campagne réactivation agressive

# RECOMMANDATIONS ACTIONNABLES

## 1. 🎯 Campagne Réactivation Prioritaire
**Cible**: 316 clients (Risque + Perdus)
**Actions**:
- Offre spéciale "Welcome Back" (-20% sur prochaine commande)
- Programme de réactivation sur 3 mois
- Budget marketing: 5% du CA potentiel

**KPIs**: Taux de conversion > 15%, ROI > 300%

## 2. 💎 Programme VIP Cluster 2
**Cible**: 51 clients High Value
**Actions**:
- Service client dédié
- Accès anticipé nouveaux produits
- Livraison gratuite illimitée
- Événements exclusifs

**KPIs**: Taux de rétention > 95%, CA par client +20%

## 3. 📈 Optimisation Cross-selling
**Cible**: 124 Clients Potentiels
**Actions**:
- Algorithmes recommandation produits
- Bundles personnalisés
- Email marketing segmenté
- Upselling au moment de l'achat

**KPIs**: Panier moyen +25%, Taux conversion +30%

## 4. 🔍 Analyse Causes Churn
**Cible**: 141 Clients Perdus
**Actions**:
- Enquêtes satisfaction sortantes
- Analyse motifs d'abandon
- Tests A/B prix/services
- Amélioration produit basée feedback

**KPIs**: Identification causes > 80%, Plan action défini

# KPIs À SURVEILLER

## 📊 Indicateurs Critiques
1. **Taux de Rétention Global**: > 85% (actuel ~60%)
2. **Panier Moyen**: > 3,500€ (actuel 2,852€)
3. **Fréquence d'Achat**: > 8 commandes/an (actuel 6.2)
4. **Valeur Vie Client (CLV)**: > 10,000€
5. **Coût Acquisition Client (CAC)**: < 200€

## 🎯 Alertes Automatiques
- Client inactivité > 90 jours
- Baisse panier moyen > 20%
- Taux churn > 5%/mois
- Satisfaction < 4/5

# PROCHAINES ÉTAPES

## 📅 Plan d'Action 30 Jours
**Semaine 1-2**: Lancement campagne réactivation
**Semaine 3**: Déploiement programme VIP
**Semaine 4**: Analyse résultats et optimisation

## 📈 Objectifs 90 Jours
- Rétention globale: 75% → 85%
- CA total: +15%
- Clients engagés: 30% → 40%
- Panier moyen: 2,852€ → 3,200€

## 🚀 Vision 6 Mois
- IA prédictive churn
- Recommandations produits temps réel
- Marketing hyper-personnalisé
- Expansion internationale

---
*Analyse générée le {datetime.now().strftime('%d/%m/%Y %H:%M')}*
*Basée sur {len(rfm_df):,} clients et clustering K-Means*
    """
    
    # Créer le rapport HTML
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rapport IA Démo - ERP Distribution</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
            .demo-badge {{ background: #ff6b6b; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #4ecdc4; color: white; border-radius: 8px; text-align: center; min-width: 140px; }}
            .metric-value {{ font-size: 20px; font-weight: bold; }}
            .metric-label {{ font-size: 11px; opacity: 0.9; }}
            .insights {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }}
            pre {{ background: #2d3748; color: #e2e8f0; padding: 20px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
            .timestamp {{ color: #718096; font-size: 12px; }}
            h1, h2, h3 {{ color: #2d3748; }}
            .highlight {{ background: #fef5e7; padding: 15px; border-left: 4px solid #f39c12; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 RAPPORT IA DÉMO - ERP DISTRIBUTION</h1>
            <p>Analyse intelligente simulée | <span class="demo-badge">MODE DÉMO</span></p>
            <p class="timestamp">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
        </div>

        <div class="section">
            <h2>📊 Vue d'ensemble</h2>
            <div class="metric">
                <div class="metric-value">{len(rfm_df):,}</div>
                <div class="metric-label">Clients Analysés</div>
            </div>
            <div class="metric">
                <div class="metric-value">{rfm_df['monetary'].mean():.0f}€</div>
                <div class="metric-label">Panier Moyen</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(rfm_df[rfm_df['segment'].isin(['Champions', 'Clients Fidèles'])])/len(rfm_df)*100:.0f}%</div>
                <div class="metric-label">Clients Engagés</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(rfm_df[rfm_df['segment'].isin(['Clients à Risque', 'Clients Perdus'])])}</div>
                <div class="metric-label">Alertes Rétention</div>
            </div>
        </div>

        <div class="section">
            <h2>🧠 Insights Générés par IA (Simulés)</h2>
            <div class="insights">
                <pre>{demo_insights}</pre>
            </div>
        </div>

        <div class="section">
            <h2>🔧 Configuration Mode Production</h2>
            <div class="highlight">
                <h3>📝 Pour passer en mode production avec vraie IA:</h3>
                <ol>
                    <li>Créez un compte OpenAI: <a href="https://platform.openai.com/">platform.openai.com</a></li>
                    <li>Générez votre clé API ($5 gratuits inclus)</li>
                    <li>Remplacez "sk-proj-demo-key-for-testing" dans olap/configs/.env</li>
                    <li>Relancez: python analytics/ia_reporting/ia_reporting.py</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Sauvegarder les rapports
    os.makedirs('analytics/results/ia_reporting/reports', exist_ok=True)
    
    with open('analytics/results/ia_reporting/reports/ia_report_demo.html', 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    with open('analytics/results/ia_reporting/reports/ia_insights_demo.md', 'w', encoding='utf-8') as f:
        f.write(demo_insights)
    
    print("✅ Rapport IA Démo généré avec succès!")
    print("📁 Fichiers créés:")
    print("  • analytics/results/ia_reporting/reports/ia_report_demo.html")
    print("  • analytics/results/ia_reporting/reports/ia_insights_demo.md")
    print("\n🚀 Pour passer en production:")
    print("  1. Obtenez une clé API sur https://platform.openai.com/")
    print("  2. Mettez à jour OPENAI_API_KEY dans olap/configs/.env")
    print("  3. Relancez avec: python analytics/ia_reporting/ia_reporting.py")

if __name__ == "__main__":
    generate_demo_ia_report()

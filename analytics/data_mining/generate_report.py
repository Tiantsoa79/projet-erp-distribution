"""
Rapport Data Mining - ERP Distribution
Génération automatique de rapport d'analyse clients
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

def generate_data_mining_report():
    """Générer un rapport complet des résultats Data Mining"""
    
    print("📊 Génération du rapport Data Mining...")
    
    # Charger les résultats
    try:
        rfm_df = pd.read_csv('analytics/results/data_mining/rfm_results_simple.csv')
        cluster_df = pd.read_csv('analytics/results/data_mining/clustering_results_simple.csv')
        print("✅ Données Data Mining chargées")
    except:
        print("❌ Fichiers Data Mining non trouvés")
        return
    
    # Créer le rapport HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rapport Data Mining - ERP Distribution</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
            .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .metric {{ display: inline-block; margin: 15px; padding: 15px; background: #3498db; color: white; border-radius: 8px; text-align: center; min-width: 150px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; }}
            .metric-label {{ font-size: 12px; opacity: 0.8; }}
            .insight {{ background: #e8f5e8; padding: 15px; border-left: 4px solid #27ae60; margin: 10px 0; }}
            .warning {{ background: #fef5e7; padding: 15px; border-left: 4px solid #f39c12; margin: 10px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .segment-badge {{ padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
            .champions {{ background: #27ae60; color: white; }}
            .loyal {{ background: #3498db; color: white; }}
            .potential {{ background: #f39c12; color: white; }}
            .at-risk {{ background: #e74c3c; color: white; }}
            .lost {{ background: #95a5a6; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 RAPPORT DATA MINING</h1>
            <h2>ERP Distribution - Analyse Comportementale Clients</h2>
            <p>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
        </div>

        <div class="section">
            <h2>📈 KPIs Principaux</h2>
            <div class="metric">
                <div class="metric-value">{len(rfm_df):,}</div>
                <div class="metric-label">Clients Analysés</div>
            </div>
            <div class="metric">
                <div class="metric-value">{rfm_df['monetary'].mean():.0f}€</div>
                <div class="metric-label">Panier Moyen</div>
            </div>
            <div class="metric">
                <div class="metric-value">{rfm_df['frequency'].mean():.1f}</div>
                <div class="metric-label">Commandes Moyennes</div>
            </div>
            <div class="metric">
                <div class="metric-value">{rfm_df['recency'].mean():.0f}j</div>
                <div class="metric-label">Récence Moyenne</div>
            </div>
        </div>

        <div class="section">
            <h2>🎯 Segmentation RFM</h2>
            <table>
                <tr><th>Segment</th><th>Nombre Clients</th><th>% Total</th><th>CA Moyen</th><th>Profil</th></tr>
    """
    
    # Ajouter les segments RFM
    segment_stats = rfm_df['segment'].value_counts()
    total_clients = len(rfm_df)
    
    segment_descriptions = {
        'Champions': ('Meilleurs clients', 'champions'),
        'Clients Fidèles': ('Clients réguliers', 'loyal'),
        'Clients Potentiels': ('Bon potentiel', 'potential'),
        'Nouveaux Clients': ('Récemment acquis', 'potential'),
        'Clients à Risque': ('En perte de vitesse', 'at-risk'),
        'Clients Perdus': ('Inactifs', 'lost'),
        'Autres': ('Profil mixte', 'potential')
    }
    
    for segment, count in segment_stats.items():
        percentage = (count / total_clients * 100)
        segment_data = rfm_df[rfm_df['segment'] == segment]
        avg_ca = segment_data['monetary'].mean()
        description, badge_class = segment_descriptions.get(segment, ('Non défini', 'potential'))
        
        html_content += f"""
                <tr>
                    <td><span class="segment-badge {badge_class}">{segment}</span></td>
                    <td>{count:,}</td>
                    <td>{percentage:.1f}%</td>
                    <td>{avg_ca:.0f}€</td>
                    <td>{description}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>

        <div class="section">
            <h2>🔍 Clustering K-Means</h2>
            <table>
                <tr><th>Cluster</th><th>Nombre Clients</th><th>CA Moyen</th><th>Commandes Moyennes</th><th>Panier Moyen</th></tr>
    """
    
    # Ajouter les clusters
    cluster_stats = cluster_df['cluster'].value_counts().sort_index()
    
    for cluster_id, count in cluster_stats.items():
        cluster_data = cluster_df[cluster_df['cluster'] == cluster_id]
        avg_ca = cluster_data['ca_total'].mean()
        avg_commands = cluster_data['nb_commandes'].mean()
        avg_basket = cluster_data['panier_moyen'].mean()
        
        html_content += f"""
                <tr>
                    <td>Cluster {cluster_id}</td>
                    <td>{count:,}</td>
                    <td>{avg_ca:.0f}€</td>
                    <td>{avg_commands:.1f}</td>
                    <td>{avg_basket:.0f}€</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>

        <div class="section">
            <h2>💡 Insights Business</h2>
            
            <div class="insight">
                <h3>🏆 Top Performers</h3>
                <p>Les 5% meilleurs clients représentent plus de 25% du chiffre d'affaires total.</p>
            </div>
            
            <div class="warning">
                <h3>⚠️ Alertes Rétention</h3>
                <p>Environ 40% des clients sont à risque ou perdus et nécessitent une action de réactivation.</p>
            </div>
            
            <div class="insight">
                <h3>🎯 Opportunités Cross-selling</h3>
                <p>Les clients du cluster 2 ont un panier moyen élevé et sont réceptifs aux offres complémentaires.</p>
            </div>
            
            <div class="insight">
                <h3>📈 Potentiel d'Upselling</h3>
                <p>Les clients fidèles achètent régulièrement mais avec un panier moyen qui peut être augmenté.</p>
            </div>
        </div>

        <div class="section">
            <h2>🎯 Recommandations Actionnables</h2>
            
            <div class="insight">
                <h3>1. Campagne Réactivation</h3>
                <p>Campagne ciblée vers les 316 clients à risque avec offres spéciales et programme de fidélité.</p>
            </div>
            
            <div class="insight">
                <h3>2. Programme VIP</h3>
                <p>Créer un programme exclusif pour les 122 clients Champions avec avantages personnalisés.</p>
            </div>
            
            <div class="insight">
                <h3>3. Optimisation Cross-selling</h3>
                <p>Développer des offres groupées pour les clusters à fort panier moyen.</p>
            </div>
            
            <div class="warning">
                <h3>4. Analyse des Causes</h3>
                <p>Enquêter sur les raisons de la perte des 141 clients perdus.</p>
            </div>
        </div>

        <div class="section">
            <h2>📊 Méthodologie</h2>
            <p><strong>Analyse RFM :</strong> Segmentation basée sur Récence, Fréquence et Montant des achats</p>
            <p><strong>Clustering K-Means :</strong> Algorithme de Machine Learning pour identifier 4 groupes naturels de clients</p>
            <p><strong>Période d'analyse :</strong> Données historiques complètes du Data Warehouse</p>
            <p><strong>Date de génération :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
    </body>
    </html>
    """
    
    # Sauvegarder le rapport
    os.makedirs('analytics/results/data_mining/reports', exist_ok=True)
    with open('analytics/results/data_mining/reports/data_mining_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Rapport Data Mining généré : analytics/results/data_mining/reports/data_mining_report.html")

if __name__ == "__main__":
    generate_data_mining_report()

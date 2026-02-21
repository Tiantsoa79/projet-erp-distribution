"""
IA Reporting - Génération automatique de rapports avec IA
Utilise une API IA gratuite en ligne pour générer des insights
"""

import pandas as pd
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv("olap/configs/.env")

class IAReporting:
    def __init__(self):
        # Configuration API IA gratuite (OpenAI compatible)
        self.api_key = os.getenv("OPENAI_API_KEY", "sk-proj-xxxxxxxx")  # À configurer
        self.api_url = "https://api.openai.com/v1/chat/completions"  # API OpenAI
        self.model = "gpt-3.5-turbo"  # Modèle gratuit
        
    def load_data_mining_results(self):
        """Charger les résultats du Data Mining"""
        try:
            rfm_df = pd.read_csv('analytics/results/data_mining/rfm_results_simple.csv')
            cluster_df = pd.read_csv('analytics/results/data_mining/clustering_results_simple.csv')
            return rfm_df, cluster_df
        except:
            return None, None
    
    def load_etl_stats(self):
        """Charger les statistiques ETL"""
        try:
            etl_df = pd.read_csv('analytics/results/etl_logs/etl_run_log.csv')
            return etl_df
        except:
            return None
    
    def generate_insights_with_ia(self, data_summary):
        """Générer des insights avec l'IA"""
        
        prompt = f"""
        En tant qu'expert en Business Intelligence et analyse de données, analyse les résultats suivants d'un système ERP Distribution et génère des insights business actionnables.

        DONNÉES À ANALYSER:
        {data_summary}

        Génère un rapport structuré avec:
        1. SYNTHÈSE EXÉCUTIVE (3-4 points clés)
        2. INSIGHTS STRATÉGIQUES (opportunités et menaces)
        3. RECOMMANDATIONS ACTIONNABLES (3-4 actions prioritaires)
        4. KPIs À SURVEILLER (indicateurs clés)
        5. PROCHAINES ÉTAPES (plan d'action)

        Style: Professionnel, concis, orienté business.
        Langue: Français.
        Format: Markdown avec titres clairs.
        """
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': 'Tu es un expert en Business Intelligence et analyse de données pour un ERP Distribution.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1500,
            'temperature': 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Erreur API: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Erreur de connexion: {str(e)}"
    
    def prepare_data_summary(self, rfm_df, cluster_df, etl_df):
        """Préparer un résumé des données pour l'IA"""
        
        summary = f"""
        === ANALYSE ERP DISTRIBUTION ===
        Date: {datetime.now().strftime('%d/%m/%Y')}
        
        --- DATA MINING RESULTS ---
        """
        
        if rfm_df is not None:
            segment_stats = rfm_df['segment'].value_counts()
            total_clients = len(rfm_df)
            avg_basket = rfm_df['monetary'].mean()
            avg_frequency = rfm_df['frequency'].mean()
            
            summary += f"""
        Clients totaux: {total_clients:,}
        Panier moyen: {avg_basket:.0f}€
        Fréquence moyenne: {avg_frequency:.1f} commandes
        
        Segmentation RFM:
        """
            for segment, count in segment_stats.items():
                percentage = (count / total_clients * 100)
                summary += f"- {segment}: {count} clients ({percentage:.1f}%)\n"
        
        if cluster_df is not None:
            cluster_stats = cluster_df['cluster'].value_counts().sort_index()
            summary += f"\n        Clustering K-Means:\n"
            for cluster_id, count in cluster_stats.items():
                cluster_data = cluster_df[cluster_df['cluster'] == cluster_id]
                avg_ca = cluster_data['ca_total'].mean()
                summary += f"- Cluster {cluster_id}: {count} clients, CA moyen {avg_ca:.0f}€\n"
        
        if etl_df is not None:
            total_records = len(etl_df)
            successful_runs = len(etl_df[etl_df['status'] == 'success'])
            summary += f"\n        --- ETL PERFORMANCE ---\n"
            summary += f"Total exécutions ETL: {total_records}\n"
            summary += f"Succès: {successful_runs} ({successful_runs/total_records*100:.1f}%)\n"
        
        return summary
    
    def generate_ia_report(self):
        """Générer le rapport IA complet"""
        
        print("🤖 Génération du rapport IA...")
        
        # Charger les données
        rfm_df, cluster_df = self.load_data_mining_results()
        etl_df = self.load_etl_stats()
        
        if rfm_df is None:
            print("❌ Données Data Mining non trouvées")
            return
        
        # Préparer le résumé
        data_summary = self.prepare_data_summary(rfm_df, cluster_df, etl_df)
        
        print("📊 Données préparées, génération des insights avec IA...")
        
        # Générer les insights avec l'IA
        ia_insights = self.generate_insights_with_ia(data_summary)
        
        # Créer le rapport HTML
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport IA - ERP Distribution</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
                .ia-badge {{ background: #ff6b6b; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #4ecdc4; color: white; border-radius: 8px; text-align: center; min-width: 140px; }}
                .metric-value {{ font-size: 20px; font-weight: bold; }}
                .metric-label {{ font-size: 11px; opacity: 0.9; }}
                .insights {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }}
                pre {{ background: #2d3748; color: #e2e8f0; padding: 20px; border-radius: 8px; overflow-x: auto; }}
                .timestamp {{ color: #718096; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 RAPPORT IA - ERP DISTRIBUTION</h1>
                <p>Analyse intelligente avec IA | <span class="ia-badge">GPT-3.5 Turbo</span></p>
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
                    <div class="metric-value">{len(rfm_df['segment'].unique())}</div>
                    <div class="metric-label">Segments Identifiés</div>
                </div>
                <div class="metric">
                    <div class="metric-value">4</div>
                    <div class="metric-label">Clusters K-Means</div>
                </div>
            </div>

            <div class="section">
                <h2>🧠 Insights Générés par IA</h2>
                <div class="insights">
                    <pre>{ia_insights}</pre>
                </div>
            </div>

            <div class="section">
                <h2>📈 Méthodologie IA</h2>
                <p><strong>Modèle utilisé:</strong> GPT-3.5 Turbo (OpenAI)</p>
                <p><strong>Approche:</strong> Analyse des patterns Data Mining + Génération d'insights business</p>
                <p><strong>Données analysées:</strong> RFM, Clustering, Performance ETL</p>
                <p><strong>Fréquence:</strong> Rapport généré à la demande</p>
            </div>

            <div class="section">
                <h2>🔄 Prochaine Génération</h2>
                <p>Les prochains rapports IA incluront:</p>
                <ul>
                    <li>Prédictions de churn</li>
                    <li>Recommandations produits personnalisées</li>
                    <li>Optimisation prix</li>
                    <li>Analyse sentiment clients</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Sauvegarder le rapport
        os.makedirs('analytics/results/ia_reporting/reports', exist_ok=True)
        
        with open('analytics/results/ia_reporting/reports/ia_report.html', 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        # Sauvegarder les insights bruts
        with open('analytics/results/ia_reporting/reports/ia_insights.md', 'w', encoding='utf-8') as f:
            f.write(f"# Rapport IA - ERP Distribution\n\n")
            f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            f.write(f"## Insights générés par IA\n\n")
            f.write(ia_insights)
        
        print("✅ Rapport IA généré avec succès!")
        print("📁 Fichiers créés:")
        print("  • analytics/results/ia_reporting/reports/ia_report.html")
        print("  • analytics/results/ia_reporting/reports/ia_insights.md")

def main():
    """Fonction principale"""
    print("🚀 Lancement du IA Reporting...")
    
    # Vérifier la clé API
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  ATTENTION: Clé API OpenAI non configurée!")
        print("📝 Pour configurer:")
        print("  1. Créez un compte OpenAI: https://platform.openai.com/")
        print("  2. Générez une clé API")
        print("  3. Ajoutez OPENAI_API_KEY=votre_clé dans olap/configs/.env")
        print("  4. Relancez ce script")
        print("\n🔄 Pour tester sans clé, utilisez le mode démo...")
        return
    
    # Générer le rapport
    ia_reporter = IAReporting()
    ia_reporter.generate_ia_report()

if __name__ == "__main__":
    main()

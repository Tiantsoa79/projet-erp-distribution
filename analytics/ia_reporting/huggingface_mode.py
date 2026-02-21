"""
IA Reporting - Version Hugging Face (GRATUIT)
Utilise les modèles gratuits de Hugging Face
"""

import pandas as pd
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv("olap/configs/.env")

class HuggingFaceReporting:
    def __init__(self):
        # Configuration Hugging Face (gratuit)
        self.api_key = os.getenv("HUGGINGFACE_API_KEY", "hf-demo-key")  # Optionnel pour certains modèles
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key != "hf-demo-key" else {},
            "Content-Type": "application/json"
        }
        
    def load_data_mining_results(self):
        """Charger les résultats du Data Mining"""
        try:
            rfm_df = pd.read_csv('analytics/results/data_mining/rfm_results_simple.csv')
            cluster_df = pd.read_csv('analytics/results/data_mining/clustering_results_simple.csv')
            return rfm_df, cluster_df
        except:
            return None, None
    
    def generate_insights_huggingface(self, data_summary):
        """Générer des insights avec Hugging Face (gratuit)"""
        
        prompt = f"""<s>[INST] Tu es un expert en Business Intelligence. Analyse ces données ERP et génère des insights actionnables:

DONNÉES:
{data_summary}

Génère un rapport structuré:
1. SYNTHÈSE EXÉCUTIVE
2. INSIGHTS STRATÉGIQUES  
3. RECOMMANDATIONS ACTIONNABLES
4. KPIs À SURVEILLER

Sois concis et orienté business. [/INST]"""
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1000,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "Erreur de génération")
                else:
                    return str(result)
            else:
                return f"Erreur API Hugging Face: {response.status_code}"
        except Exception as e:
            return f"Erreur de connexion: {str(e)}"
    
    def prepare_data_summary(self, rfm_df, cluster_df):
        """Préparer résumé pour l'IA"""
        summary = f"""
=== ERP DISTRIBUTION - ANALYSE CLIENTS ===
Date: {datetime.now().strftime('%d/%m/%Y')}

--- SEGMENTATION RFM ---
Clients totaux: {len(rfm_df):,}
Panier moyen: {rfm_df['monetary'].mean():.0f}€
Fréquence moyenne: {rfm_df['frequency'].mean():.1f} commandes

Segments:
"""
        segment_stats = rfm_df['segment'].value_counts()
        total_clients = len(rfm_df)
        
        for segment, count in segment_stats.items():
            percentage = (count / total_clients * 100)
            summary += f"- {segment}: {count} clients ({percentage:.1f}%)\n"
        
        if cluster_df is not None:
            cluster_stats = cluster_df['cluster'].value_counts().sort_index()
            summary += f"\n--- CLUSTERING K-MEANS ---\n"
            for cluster_id, count in cluster_stats.items():
                cluster_data = cluster_df[cluster_df['cluster'] == cluster_id]
                avg_ca = cluster_data['ca_total'].mean()
                summary += f"- Cluster {cluster_id}: {count} clients, CA moyen {avg_ca:.0f}€\n"
        
        return summary
    
    def generate_hf_report(self):
        """Générer rapport Hugging Face"""
        
        print("🤗 Génération rapport Hugging Face (GRATUIT)...")
        
        # Charger données
        rfm_df, cluster_df = self.load_data_mining_results()
        
        if rfm_df is None:
            print("❌ Données Data Mining non trouvées")
            return
        
        # Préparer résumé
        data_summary = self.prepare_data_summary(rfm_df, cluster_df)
        
        print("📊 Données préparées, génération insights avec Hugging Face...")
        
        # Générer insights
        hf_insights = self.generate_insights_huggingface(data_summary)
        
        # Créer rapport HTML
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport Hugging Face - ERP Distribution</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
                .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
                .hf-badge {{ background: #48dbfb; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #ff9ff3; color: white; border-radius: 8px; text-align: center; min-width: 140px; }}
                .metric-value {{ font-size: 20px; font-weight: bold; }}
                .metric-label {{ font-size: 11px; opacity: 0.9; }}
                .insights {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }}
                pre {{ background: #2d3748; color: #e2e8f0; padding: 20px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
                .timestamp {{ color: #718096; font-size: 12px; }}
                .free-badge {{ background: #00d2d3; color: white; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤗 RAPPORT HUGGING FACE - ERP DISTRIBUTION</h1>
                <p>Analyse IA gratuite | <span class="hf-badge">Mistral-7B</span> | <span class="free-badge">100% GRATUIT</span></p>
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
                    <div class="metric-label">Segments RFM</div>
                </div>
                <div class="metric">
                    <div class="metric-value">4</div>
                    <div class="metric-label">Clusters K-Means</div>
                </div>
            </div>

            <div class="section">
                <h2>🤗 Insights Hugging Face (Mistral-7B)</h2>
                <div class="insights">
                    <pre>{hf_insights}</pre>
                </div>
            </div>

            <div class="section">
                <h2>🆓 Avantages Hugging Face</h2>
                <ul>
                    <li>✅ 100% Gratuit - pas de limite mensuelle</li>
                    <li>🚀 Mistral-7B - qualité équivalente GPT-3.5</li>
                    <li>🔧 Pas d'inscription requise pour usage basique</li>
                    <li>⚡ Rapide - réponse en 2-3 secondes</li>
                    <li>🌍 Open source - modèle transparent</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Sauvegarder
        os.makedirs('analytics/results/ia_reporting/reports', exist_ok=True)
        
        with open('analytics/results/ia_reporting/reports/hf_report.html', 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        with open('analytics/results/ia_reporting/reports/hf_insights.md', 'w', encoding='utf-8') as f:
            f.write(f"# Rapport Hugging Face - ERP Distribution\n\n")
            f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            f.write(f"## Insights Hugging Face (Mistral-7B)\n\n")
            f.write(hf_insights)
        
        print("✅ Rapport Hugging Face généré avec succès!")
        print("📁 Fichiers créés:")
        print("  • analytics/results/ia_reporting/reports/hf_report.html")
        print("  • analytics/results/ia_reporting/reports/hf_insights.md")

def main():
    """Fonction principale"""
    print("🚀 Lancement IA Reporting Hugging Face (GRATUIT)...")
    
    # Vérifier configuration
    if not os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HUGGINGFACE_API_KEY") == "hf-demo-key":
        print("⚠️  Clé Hugging Face non configurée - utilisation mode limité")
        print("📝 Pour configuration complète:")
        print("  1. Créez compte: https://huggingface.co/")
        print("  2. Générez token: Settings → Access Tokens")
        print("  3. Ajoutez HUGGINGFACE_API_KEY=votre_token dans olap/configs/.env")
        print("\n🔄 Mode démo disponible quand même...")
    
    # Générer rapport
    hf_reporter = HuggingFaceReporting()
    hf_reporter.generate_hf_report()

if __name__ == "__main__":
    main()

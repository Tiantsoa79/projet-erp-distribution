"""
Génération d'Insights Automatiques

Utilise des algorithmes de ML et LLM pour générer des insights
business pertinents à partir des données de l'ERP.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

class InsightGenerator:
    def __init__(self, llm_api_key=None):
        self.conn = get_connection()
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY")
        
    def load_business_data(self):
        """Charger les données business pour l'analyse"""
        
        queries = {
            'sales_trend': """
                SELECT 
                    dd.month_name,
                    dd.year_number,
                    SUM(fo.total_amount) as ca_mensuel,
                    COUNT(DISTINCT fo.order_key) as nb_commandes,
                    COUNT(DISTINCT fo.customer_key) as nb_clients,
                    AVG(fo.total_amount) as panier_moyen
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.year_number >= EXTRACT(YEAR FROM CURRENT_DATE) - 1
                GROUP BY dd.year_number, dd.month_name
                ORDER BY dd.year_number, dd.month_name
            """,
            
            'product_performance': """
                SELECT 
                    dp.product_category,
                    SUM(fol.line_amount) as ca_categorie,
                    SUM(fol.quantity) as quantite_vendue,
                    COUNT(DISTINCT fol.order_line_key) as nb_ventes,
                    COUNT(DISTINCT dp.product_key) as nb_produits
                FROM dwh.dim_product dp
                JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
                WHERE fol.order_line_key IS NOT NULL
                GROUP BY dp.product_category
                ORDER BY ca_categorie DESC
            """,
            
            'customer_behavior': """
                SELECT 
                    dc.customer_key,
                    dc.customer_name,
                    COUNT(DISTINCT fo.order_key) as nb_commandes,
                    SUM(fo.total_amount) as ca_total,
                    AVG(fo.total_amount) as panier_moyen,
                    MIN(dd.full_date) as premiere_commande,
                    MAX(dd.full_date) as derniere_commande
                FROM dwh.dim_customer dc
                LEFT JOIN dwh.fact_orders fo ON dc.customer_key = fo.customer_key
                LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE fo.order_date_key IS NOT NULL
                GROUP BY dc.customer_key, dc.customer_name
            """,
            
            'geographic_analysis': """
                SELECT 
                    dg.country,
                    dg.region,
                    SUM(fo.total_amount) as ca_pays,
                    COUNT(DISTINCT fo.order_key) as nb_commandes,
                    COUNT(DISTINCT fo.customer_key) as nb_clients,
                    AVG(fo.total_amount) as panier_moyen
                FROM dwh.fact_orders fo
                JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
                GROUP BY dg.country, dg.region
                ORDER BY ca_pays DESC
            """
        }
        
        data = {}
        for key, query in queries.items():
            data[key] = pd.read_sql(query, self.conn)
        
        return data
    
    def detect_anomalies(self, df, column_name):
        """Détecter les anomalies dans une colonne"""
        
        if column_name not in df.columns:
            return []
        
        values = df[column_name].values.reshape(-1, 1)
        
        # Standardisation
        scaler = StandardScaler()
        values_scaled = scaler.fit_transform(values)
        
        # Isolation Forest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        anomaly_labels = iso_forest.fit_predict(values_scaled)
        
        # Identifier les anomalies
        anomalies = []
        for i, label in enumerate(anomaly_labels):
            if label == -1:
                anomalies.append({
                    'index': i,
                    'value': df.iloc[i][column_name],
                    'context': df.iloc[i].to_dict()
                })
        
        return anomalies
    
    def generate_trend_insights(self, sales_data):
        """Générer des insights sur les tendances"""
        
        insights = []
        
        # Analyse de croissance
        if len(sales_data) >= 2:
            recent_months = sales_data.tail(3)
            previous_months = sales_data.tail(6).head(3)
            
            recent_avg = recent_months['ca_mensuel'].mean()
            previous_avg = previous_months['ca_mensuel'].mean()
            
            growth_rate = ((recent_avg - previous_avg) / previous_avg) * 100
            
            if growth_rate > 10:
                insights.append({
                    'type': 'positive_trend',
                    'title': '📈 Forte croissance détectée',
                    'description': f"Le CA a augmenté de {growth_rate:.1f}% sur les 3 derniers mois",
                    'impact': 'high',
                    'recommendation': 'Consolider les stratégies actuelles et prévoir l\'expansion'
                })
            elif growth_rate < -10:
                insights.append({
                    'type': 'negative_trend',
                    'title': '📉 Baisse inquiétante',
                    'description': f"Le CA a baissé de {abs(growth_rate):.1f}% sur les 3 derniers mois",
                    'impact': 'high',
                    'recommendation': 'Analyser les causes et mettre en place des actions correctives'
                })
        
        # Détection d'anomalies
        anomalies = self.detect_anomalies(sales_data, 'ca_mensuel')
        for anomaly in anomalies:
            insights.append({
                'type': 'anomaly',
                'title': '🚨 Anomalie de ventes détectée',
                'description': f"CA anormal de {anomaly['value']:,.0f} € en {anomaly['context']['month_name']} {anomaly['context']['year_number']}",
                'impact': 'medium',
                'recommendation': 'Vérifier les données et analyser les causes de cette variation'
            })
        
        return insights
    
    def generate_product_insights(self, product_data):
        """Générer des insights sur les produits"""
        
        insights = []
        
        # Top et bottom catégories
        if len(product_data) > 0:
            top_category = product_data.iloc[0]
            bottom_category = product_data.iloc[-1]
            
            # 80/20 rule
            total_ca = product_data['ca_categorie'].sum()
            top_80_percent = product_data[product_data['ca_categorie'].cumsum() <= total_ca * 0.8]
            
            if len(top_80_percent) < len(product_data) * 0.5:
                insights.append({
                    'type': 'pareto_analysis',
                    'title': '📊 Principe 80/20 confirmé',
                    'description': f"{len(top_80_percent)} catégories génèrent 80% du CA",
                    'impact': 'high',
                    'recommendation': 'Focaliser les efforts sur les catégories les plus rentables'
                })
            
            # Catégorie en baisse
            if len(product_data) >= 2:
                growth_rates = []
                for i in range(1, len(product_data)):
                    if product_data.iloc[i]['quantite_vendue'] > 0:
                        prev_qty = product_data.iloc[i-1]['quantite_vendue']
                        curr_qty = product_data.iloc[i]['quantite_vendue']
                        if prev_qty > 0:
                            growth_rates.append((curr_qty - prev_qty) / prev_qty * 100)
                
                if growth_rates and min(growth_rates) < -20:
                    insights.append({
                        'type': 'category_decline',
                        'title': '📉 Catégorie en déclin',
                        'description': f"Une catégorie montre une baisse de plus de 20%",
                        'impact': 'medium',
                        'recommendation': 'Analyser les causes et envisager des promotions'
                    })
        
        return insights
    
    def generate_customer_insights(self, customer_data):
        """Générer des insights sur les clients"""
        
        insights = []
        
        # Segmentation RFM simplifiée
        active_customers = customer_data[customer_data['nb_commandes'] > 0]
        
        if len(active_customers) > 0:
            # Top 10% des clients
            ca_threshold = active_customers['ca_total'].quantile(0.9)
            top_clients = active_customers[active_customers['ca_total'] >= ca_threshold]
            
            if len(top_clients) > 0:
                top_ca_percentage = top_clients['ca_total'].sum() / active_customers['ca_total'].sum() * 100
                
                insights.append({
                    'type': 'customer_concentration',
                    'title': '👥 Concentration client forte',
                    'description': f"Les 10% meilleurs clients représentent {top_ca_percentage:.1f}% du CA",
                    'impact': 'high',
                    'recommendation': 'Mettre en place un programme de fidélité pour les meilleurs clients'
                })
            
            # Clients inactifs
            inactive_threshold = datetime.now() - timedelta(days=90)
            inactive_customers = active_customers[
                pd.to_datetime(active_customers['derniere_commande']) < inactive_threshold
            ]
            
            if len(inactive_customers) > len(active_customers) * 0.3:
                insights.append({
                    'type': 'customer_churn',
                    'title': '⚠️ Taux d\'attrition élevé',
                    'description': f"{len(inactive_customers)} clients n'ont pas commandé depuis 90 jours",
                    'impact': 'high',
                    'recommendation': 'Lancer une campagne de réactivation pour les clients inactifs'
                })
        
        return insights
    
    def generate_llm_insights(self, data_summary):
        """Utiliser LLM pour générer des insights business"""
        
        if not self.llm_api_key:
            return []
        
        # Préparer le contexte pour le LLM
        context = f"""
        Données business ERP Distribution:
        - Ventes mensuelles moyennes: {data_summary.get('avg_monthly_sales', 0):,.0f} €
        - Nombre de catégories produits: {data_summary.get('product_categories', 0)}
        - Nombre de clients actifs: {data_summary.get('active_customers', 0)}
        - Pays principaux: {data_summary.get('top_countries', [])[:3]}
        
        Génère 3 insights business stratégiques basés sur ces données.
        Format JSON avec: type, title, description, impact (low/medium/high), recommendation
        """
        
        try:
            # Appel à l'API OpenAI (ou autre LLM)
            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Tu es un expert en analyse business et data science.'},
                    {'role': 'user', 'content': context}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parser la réponse JSON
                try:
                    llm_insights = json.loads(content)
                    return llm_insights if isinstance(llm_insights, list) else []
                except:
                    return []
            
        except Exception as e:
            print(f"Erreur LLM: {e}")
            return []
        
        return []
    
    def generate_insights_report(self):
        """Générer un rapport complet d'insights"""
        
        print("🧠 Génération des insights business...")
        
        # Charger les données
        data = self.load_business_data()
        
        # Résumé pour LLM
        data_summary = {
            'avg_monthly_sales': data['sales_trend']['ca_mensuel'].mean() if not data['sales_trend'].empty else 0,
            'product_categories': len(data['product_performance']) if not data['product_performance'].empty else 0,
            'active_customers': len(data['customer_behavior'][data['customer_behavior']['nb_commandes'] > 0]) if not data['customer_behavior'].empty else 0,
            'top_countries': data['geographic_analysis']['country'].head(5).tolist() if not data['geographic_analysis'].empty else []
        }
        
        # Générer les insights
        all_insights = []
        
        # Insights tendances
        all_insights.extend(self.generate_trend_insights(data['sales_trend']))
        
        # Insights produits
        all_insights.extend(self.generate_product_insights(data['product_performance']))
        
        # Insights clients
        all_insights.extend(self.generate_customer_insights(data['customer_behavior']))
        
        # Insights LLM
        llm_insights = self.generate_llm_insights(data_summary)
        all_insights.extend(llm_insights)
        
        # Trier par impact
        impact_order = {'high': 3, 'medium': 2, 'low': 1}
        all_insights.sort(key=lambda x: impact_order.get(x['impact'], 0), reverse=True)
        
        # Générer le rapport
        self.display_insights_report(all_insights)
        
        # Sauvegarder
        self.save_insights_report(all_insights)
        
        return all_insights
    
    def display_insights_report(self, insights):
        """Afficher le rapport d'insights"""
        
        print("\n" + "="*80)
        print("🧠 RAPPORT D'INSIGHTS BUSINESS - ERP DISTRIBUTION")
        print("="*80)
        
        for i, insight in enumerate(insights, 1):
            impact_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(insight['impact'], '⚪')
            
            print(f"\n{i}. {insight['title']} {impact_emoji}")
            print(f"   📝 {insight['description']}")
            print(f"   💡 {insight['recommendation']}")
            print(f"   🎯 Impact: {insight['impact'].upper()}")
            print("-" * 60)
        
        print(f"\n✅ Total: {len(insights)} insights générés")
    
    def save_insights_report(self, insights):
        """Sauvegarder le rapport d'insights"""
        
        # Créer un DataFrame
        df = pd.DataFrame(insights)
        
        # Sauvegarder en CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'analytics/ai_reporting/insights_{timestamp}.csv'
        df.to_csv(filename, index=False)
        
        # Sauvegarder en JSON
        json_filename = f'analytics/ai_reporting/insights_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Rapport sauvegardé:")
        print(f"  📄 CSV: {filename}")
        print(f"  📄 JSON: {json_filename}")
    
    def close(self):
        """Fermer la connexion"""
        self.conn.close()

def main():
    """Fonction principale"""
    print("🚀 Lancement du générateur d'insights IA...")
    
    generator = InsightGenerator()
    
    try:
        insights = generator.generate_insights_report()
        print(f"\n🎯 {len(insights)} insights business générés avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        generator.close()

if __name__ == "__main__":
    main()

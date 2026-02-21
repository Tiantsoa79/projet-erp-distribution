"""
Data Storytelling Automatisé

Crée des histoires de données engageantes et des rapports narratifs
basés sur les insights de l'ERP.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

class DataStoryteller:
    def __init__(self, llm_api_key=None):
        self.conn = get_connection()
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY")
        
    def load_story_data(self):
        """Charger les données pour le storytelling"""
        
        queries = {
            'business_overview': """
                SELECT 
                    COUNT(DISTINCT fo.order_key) as total_orders,
                    SUM(fo.total_amount) as total_revenue,
                    COUNT(DISTINCT fo.customer_key) as total_customers,
                    COUNT(DISTINCT dp.product_key) as total_products,
                    COUNT(DISTINCT dg.country) as total_countries,
                    MIN(dd.full_date) as first_order_date,
                    MAX(dd.full_date) as last_order_date
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                LEFT JOIN dwh.fact_order_lines fol ON fo.order_key = fol.order_key
                LEFT JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
                LEFT JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
            """,
            
            'monthly_evolution': """
                SELECT 
                    dd.year_number,
                    dd.month_name,
                    dd.full_date,
                    SUM(fo.total_amount) as monthly_revenue,
                    COUNT(DISTINCT fo.order_key) as monthly_orders,
                    COUNT(DISTINCT fo.customer_key) as monthly_customers
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY dd.year_number, dd.month_name, dd.full_date
                ORDER BY dd.full_date
            """,
            
            'product_stars': """
                SELECT 
                    dp.product_name,
                    dp.product_category,
                    SUM(fol.line_amount) as product_revenue,
                    SUM(fol.quantity) as total_quantity,
                    COUNT(DISTINCT fol.order_line_key) as order_count
                FROM dwh.dim_product dp
                JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
                GROUP BY dp.product_key, dp.product_name, dp.product_category
                ORDER BY product_revenue DESC
                LIMIT 10
            """,
            
            'geographic_story': """
                SELECT 
                    dg.country,
                    dg.region,
                    SUM(fo.total_amount) as country_revenue,
                    COUNT(DISTINCT fo.order_key) as country_orders,
                    COUNT(DISTINCT fo.customer_key) as country_customers,
                    COUNT(DISTINCT dp.product_key) as country_products
                FROM dwh.fact_orders fo
                JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
                LEFT JOIN dwh.fact_order_lines fol ON fo.order_key = fol.order_key
                LEFT JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
                GROUP BY dg.country, dg.region
                ORDER BY country_revenue DESC
                LIMIT 15
            """,
            
            'customer_journey': """
                WITH customer_lifecycle AS (
                    SELECT 
                        dc.customer_key,
                        dc.customer_name,
                        MIN(dd.full_date) as first_order,
                        MAX(dd.full_date) as last_order,
                        COUNT(DISTINCT fo.order_key) as total_orders,
                        SUM(fo.total_amount) as lifetime_value,
                        AVG(fo.total_amount) as avg_order_value
                    FROM dwh.dim_customer dc
                    JOIN dwh.fact_orders fo ON dc.customer_key = fo.customer_key
                    JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                    WHERE fo.total_amount > 0
                    GROUP BY dc.customer_key, dc.customer_name
                )
                SELECT 
                    CASE 
                        WHEN total_orders = 1 THEN 'Nouveau'
                        WHEN total_orders BETWEEN 2 AND 5 THEN 'Débutant'
                        WHEN total_orders BETWEEN 6 AND 15 THEN 'Habitué'
                        WHEN total_orders > 15 THEN 'VIP'
                    END as customer_segment,
                    COUNT(*) as customer_count,
                    AVG(lifetime_value) as avg_lifetime_value,
                    AVG(avg_order_value) as avg_order_value
                FROM customer_lifecycle
                GROUP BY customer_segment
                ORDER BY avg_lifetime_value DESC
            """
        }
        
        data = {}
        for key, query in queries.items():
            data[key] = pd.read_sql(query, self.conn)
        
        return data
    
    def generate_story_theme(self, data):
        """Déterminer le thème principal de l'histoire"""
        
        if data['business_overview'].empty:
            return "Aperçu Business"
        
        overview = data['business_overview'].iloc[0]
        
        # Analyser les tendances pour déterminer le thème
        if len(data['monthly_evolution']) >= 2:
            recent_growth = self.calculate_growth_rate(data['monthly_evolution'].tail(3)['monthly_revenue'])
            
            if recent_growth > 15:
                return "Croissance Exceptionnelle"
            elif recent_growth > 5:
                return "Expansion Stratégique"
            elif recent_growth < -10:
                return "Transformation Nécessaire"
        
        # Analyser la performance produits
        if not data['product_stars'].empty:
            top_product = data['product_stars'].iloc[0]
            if top_product['product_revenue'] > overview['total_revenue'] * 0.05:
                return "Le Produit Phare"
        
        # Analyser la géographie
        if not data['geographic_story'].empty:
            top_country = data['geographic_story'].iloc[0]
            if top_country['country_revenue'] > overview['total_revenue'] * 0.3:
                return "Conquête de Marché"
        
        return "Performance Business"
    
    def calculate_growth_rate(self, values):
        """Calculer le taux de croissance"""
        if len(values) < 2:
            return 0
        return ((values.iloc[-1] - values.iloc[0]) / values.iloc[0]) * 100
    
    def generate_llm_story(self, theme, data_summary):
        """Utiliser LLM pour générer l'histoire narrative"""
        
        if not self.llm_api_key:
            return self.generate_basic_story(theme, data_summary)
        
        context = f"""
        Thème: {theme}
        
        Données clés ERP Distribution:
        - Chiffre d'affaires total: {data_summary.get('total_revenue', 0):,.0f} €
        - Nombre total de commandes: {data_summary.get('total_orders', 0):,}
        - Nombre de clients: {data_summary.get('total_customers', 0):,}
        - Nombre de produits: {data_summary.get('total_products', 0):,}
        - Pays desservis: {data_summary.get('total_countries', 0)}
        - Croissance récente: {data_summary.get('recent_growth', 0):.1f}%
        - Produit phare: {data_summary.get('top_product', 'N/A')}
        - Marché principal: {data_summary.get('top_market', 'N/A')}
        
        Génère une histoire business engageante (300-500 mots) avec:
        1. Un titre accrocheur
        2. Une introduction qui pose le contexte
        3. 2-3 paragraphes de développement avec chiffres clés
        4. Une conclusion avec perspectives d'avenir
        5. 3 points clés à retenir
        
        Style: professionnel mais accessible, comme pour un comité de direction.
        """
        
        try:
            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Tu es un expert en storytelling business et data journalisme.'},
                    {'role': 'user', 'content': context}
                ],
                'temperature': 0.8,
                'max_tokens': 800
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            
        except Exception as e:
            print(f"Erreur LLM storytelling: {e}")
            return self.generate_basic_story(theme, data_summary)
        
        return self.generate_basic_story(theme, data_summary)
    
    def generate_basic_story(self, theme, data_summary):
        """Générer une histoire de base sans LLM"""
        
        stories = {
            "Croissance Exceptionnelle": f"""
            🚀 {theme}: L'histoire d'une croissance remarquable
            
            Au cours des derniers mois, ERP Distribution a connu une trajectoire de croissance exceptionnelle. 
            Avec un chiffre d'affaires de {data_summary.get('total_revenue', 0):,.0f} € et {data_summary.get('total_orders', 0):,} commandes,
            l'entreprise démontre une vitalité économique impressionnante.
            
            Cette performance s'appuie sur {data_summary.get('total_customers', 0):,} clients fidèles et {data_summary.get('total_products', 0):,} produits innovants.
            La croissance de {data_summary.get('recent_growth', 0):.1f}% témoigne de l'efficacité de nos stratégies commerciales.
            
            Perspectives: Cette dynamique nous positionne favorablement pour une expansion continue 
            et le renforcement de notre part de marché.
            """,
            
            "Performance Business": f"""
            📊 {theme}: Une analyse de notre performance business
            
            ERP Distribution affiche des résultats solides avec {data_summary.get('total_revenue', 0):,.0f} € de chiffre d'affaires
            généré par {data_summary.get('total_orders', 0):,} commandes auprès de {data_summary.get('total_customers', 0):,} clients.
            
            Notre portefeuille de {data_summary.get('total_products', 0):,} produits et notre présence sur {data_summary.get('total_countries', 0)} marchés
            constituent les fondations de cette performance stable.
            
            L'analyse révèle des opportunités d'optimisation dans nos processus opérationnels 
            et notre stratégie commerciale.
            
            Perspectives: La consolidation de nos acquis et l'exploitation des leviers de croissance 
            seront les priorités des prochains trimestres.
            """
",
            
            "Le Produit Phare": f"""
            ⭐ {theme}: Quand un produit change la donne
            
            Dans l'écosystème d'ERP Distribution, {data_summary.get('top_product', 'un produit')} 
            s'est imposé comme le véritable moteur de notre performance.
            
            Avec un chiffre d'affaires total de {data_summary.get('total_revenue', 0):,.0f} €, 
            ce produit phare illustre notre capacité à identifier et développer des offres gagnantes.
            
            Son succès repose sur une compréhension fine des besoins clients 
            et une exécution opérationnelle irréprochable.
            
            Perspectives: L'objectif est de répliquer ce modèle de succès 
            sur d'autres segments de notre portefeuille.
            """
        }
        
        return stories.get(theme, stories["Performance Business"])
    
    def create_story_visualizations(self, data, theme):
        """Créer les visualisations pour l'histoire"""
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Data Story: {theme}', fontsize=16, fontweight='bold')
        
        # 1. Évolution mensuelle
        if not data['monthly_evolution'].empty:
            monthly_data = data['monthly_evolution']
            axes[0, 0].plot(pd.to_datetime(monthly_data['full_date']), monthly_data['monthly_revenue'], 
                            marker='o', linewidth=2, color='#2ecc71')
            axes[0, 0].set_title('Évolution du Chiffre d\'Affaires')
            axes[0, 0].set_xlabel('Mois')
            axes[0, 0].set_ylabel('CA (€)')
            axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. Top produits
        if not data['product_stars'].empty:
            top_products = data['product_stars'].head(5)
            axes[0, 1].barh(range(len(top_products)), top_products['product_revenue'], color='#3498db')
            axes[0, 1].set_title('Top 5 Produits par CA')
            axes[0, 1].set_xlabel('CA (€)')
            axes[0, 1].set_yticks(range(len(top_products)))
            axes[0, 1].set_yticklabels([p[:25] for p in top_products['product_name']])
        
        # 3. Répartition géographique
        if not data['geographic_story'].empty:
            geo_data = data['geographic_story'].head(8)
            axes[1, 0].pie(geo_data['country_revenue'], labels=geo_data['country'], autopct='%1.1f%%')
            axes[1, 0].set_title('Répartition du CA par Pays')
        
        # 4. Segmentation clients
        if not data['customer_journey'].empty:
            customer_segments = data['customer_journey']
            axes[1, 1].bar(customer_segments['customer_segment'], customer_segments['avg_lifetime_value'], 
                            color='#e74c3c')
            axes[1, 1].set_title('Valeur Moyenne par Segment Client')
            axes[1, 1].set_xlabel('Segment')
            axes[1, 1].set_ylabel('Valeur Vie Client (€)')
            axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Sauvegarder la visualisation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'analytics/ai_reporting/story_visualization_{timestamp}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.show()
        
        return filename
    
    def generate_story_report(self):
        """Générer un rapport complet de storytelling"""
        
        print("📚 Génération du Data Storytelling...")
        
        # Charger les données
        data = self.load_story_data()
        
        # Déterminer le thème
        theme = self.generate_story_theme(data)
        
        # Préparer le résumé pour LLM
        overview = data['business_overview'].iloc[0] if not data['business_overview'].empty else {}
        data_summary = {
            'total_revenue': overview.get('total_revenue', 0),
            'total_orders': overview.get('total_orders', 0),
            'total_customers': overview.get('total_customers', 0),
            'total_products': overview.get('total_products', 0),
            'total_countries': overview.get('total_countries', 0),
            'recent_growth': self.calculate_growth_rate(data['monthly_evolution']['monthly_revenue']) if not data['monthly_evolution'].empty else 0,
            'top_product': data['product_stars'].iloc[0]['product_name'] if not data['product_stars'].empty else 'N/A',
            'top_market': data['geographic_story'].iloc[0]['country'] if not data['geographic_story'].empty else 'N/A'
        }
        
        # Générer l'histoire
        story = self.generate_llm_story(theme, data_summary)
        
        # Créer les visualisations
        viz_filename = self.create_story_visualizations(data, theme)
        
        # Afficher et sauvegarder
        self.display_story_report(theme, story, data_summary, viz_filename)
        self.save_story_report(theme, story, data_summary)
        
        return story
    
    def display_story_report(self, theme, story, data_summary, viz_filename):
        """Afficher le rapport de storytelling"""
        
        print("\n" + "="*80)
        print(f"📚 DATA STORYTELLING - {theme}")
        print("="*80)
        
        print(f"\n📊 Résumé des Données Clés:")
        print(f"  💰 Chiffre d'affaires: {data_summary.get('total_revenue', 0):,.0f} €")
        print(f"  📦 Commandes totales: {data_summary.get('total_orders', 0):,}")
        print(f"  👥 Clients: {data_summary.get('total_customers', 0):,}")
        print(f"  🏭 Produits: {data_summary.get('total_products', 0):,}")
        print(f"  🌍 Pays: {data_summary.get('total_countries', 0)}")
        print(f"  📈 Croissance: {data_summary.get('recent_growth', 0):.1f}%")
        
        print(f"\n📖 Histoire Business:")
        print(story)
        
        print(f"\n📈 Visualisation: {viz_filename}")
    
    def save_story_report(self, theme, story, data_summary):
        """Sauvegarder le rapport de storytelling"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarder en Markdown
        markdown_content = f"""# Data Story: {theme}

*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*

## 📊 Résumé des Données

- **Chiffre d'affaires**: {data_summary.get('total_revenue', 0):,.0f} €
- **Commandes totales**: {data_summary.get('total_orders', 0):,}
- **Clients**: {data_summary.get('total_customers', 0):,}
- **Produits**: {data_summary.get('total_products', 0):,}
- **Pays desservis**: {data_summary.get('total_countries', 0)}
- **Croissance récente**: {data_summary.get('recent_growth', 0):.1f}%

## 📖 Histoire Business

{story}

## 🎯 Points Clés à Retenir

1. Performance commerciale solide avec croissance significative
2. Portefeuille produits diversifié et attractif
3. Base clients fidèle et en expansion

## 📈 Perspectives d'Avenir

- Poursuite de l'expansion géographique
- Optimisation des processus opérationnels
- Renforcement des programmes de fidélité client
"""
        
        markdown_filename = f'analytics/ai_reporting/story_{timestamp}.md'
        with open(markdown_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Sauvegarder en JSON
        json_data = {
            'theme': theme,
            'story': story,
            'data_summary': data_summary,
            'generated_at': datetime.now().isoformat()
        }
        
        json_filename = f'analytics/ai_reporting/story_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Rapport sauvegardé:")
        print(f"  📄 Markdown: {markdown_filename}")
        print(f"  📄 JSON: {json_filename}")
    
    def close(self):
        """Fermer la connexion"""
        self.conn.close()

def main():
    """Fonction principale"""
    print("🚀 Lancement du Data Storytelling IA...")
    
    storyteller = DataStoryteller()
    
    try:
        story = storyteller.generate_story_report()
        print(f"\n📚 Histoire business générée avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        storyteller.close()

if __name__ == "__main__":
    main()

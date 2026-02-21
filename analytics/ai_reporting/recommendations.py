"""
Génération de Recommandations Stratégiques

Utilise l'IA pour générer des recommandations actionnables
basées sur les données de l'ERP et les meilleures pratiques.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

class RecommendationEngine:
    def __init__(self, llm_api_key=None):
        self.conn = get_connection()
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY")
        
    def load_performance_data(self):
        """Charger les données de performance pour les recommandations"""
        
        queries = {
            'sales_performance': """
                SELECT 
                    dd.month_name,
                    dd.year_number,
                    SUM(fo.total_amount) as ca_mensuel,
                    COUNT(DISTINCT fo.order_key) as nb_commandes,
                    COUNT(DISTINCT fo.customer_key) as nb_clients,
                    AVG(fo.total_amount) as panier_moyen,
                    EXTRACT(DAY FROM dd.full_date) as day_of_month
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY dd.year_number, dd.month_name, EXTRACT(DAY FROM dd.full_date)
                ORDER BY dd.full_date
            """,
            
            'product_margins': """
                SELECT 
                    dp.product_name,
                    dp.product_category,
                    dp.unit_price as cost_price,
                    AVG(fol.unit_price) as avg_selling_price,
                    SUM(fol.quantity) as total_quantity,
                    SUM(fol.line_amount) as total_revenue,
                    (AVG(fol.unit_price) - dp.unit_price) * 100 / dp.unit_price as margin_percentage
                FROM dwh.dim_product dp
                JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
                WHERE fol.order_line_key IS NOT NULL
                  AND dp.unit_price > 0
                GROUP BY dp.product_key, dp.product_name, dp.product_category, dp.unit_price
                HAVING SUM(fol.quantity) > 0
                ORDER BY margin_percentage ASC
            """,
            
            'inventory_turnover': """
                SELECT 
                    dp.product_name,
                    dp.product_category,
                    SUM(fis.quantity_on_hand) as current_stock,
                    AVG(fis.quantity_on_hand) as avg_stock,
                    SUM(fol.quantity) as quantity_sold,
                    CASE 
                        WHEN AVG(fis.quantity_on_hand) > 0 
                        THEN SUM(fol.quantity) * 365.0 / AVG(fis.quantity_on_hand)
                        ELSE 0
                    END as turnover_rate
                FROM dwh.dim_product dp
                LEFT JOIN dwh.fact_inventory_snapshot fis ON dp.product_key = fis.product_key
                LEFT JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
                WHERE fis.snapshot_date_key >= (SELECT MAX(snapshot_date_key) - 30 FROM dwh.fact_inventory_snapshot)
                GROUP BY dp.product_key, dp.product_name, dp.product_category
                HAVING SUM(fol.quantity) > 0 OR AVG(fis.quantity_on_hand) > 0
                ORDER BY turnover_rate ASC
            """,
            
            'customer_lifetime_value': """
                WITH customer_metrics AS (
                    SELECT 
                        dc.customer_key,
                        dc.customer_name,
                        COUNT(DISTINCT fo.order_key) as nb_commandes,
                        SUM(fo.total_amount) as total_spent,
                        MIN(dd.full_date) as first_order,
                        MAX(dd.full_date) as last_order,
                        EXTRACT(DAYS FROM (MAX(dd.full_date) - MIN(dd.full_date))) as customer_lifetime_days
                    FROM dwh.dim_customer dc
                    JOIN dwh.fact_orders fo ON dc.customer_key = fo.customer_key
                    JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                    WHERE fo.total_amount > 0
                    GROUP BY dc.customer_key, dc.customer_name
                )
                SELECT 
                    customer_key,
                    customer_name,
                    nb_commandes,
                    total_spent,
                    first_order,
                    last_order,
                    customer_lifetime_days,
                    CASE 
                        WHEN customer_lifetime_days > 0 
                        THEN total_spent * 365.0 / customer_lifetime_days
                        ELSE total_spent
                    END as annual_value,
                    total_spent * 1.0 / nb_commandes as avg_order_value
                FROM customer_metrics
                ORDER BY annual_value DESC
            """
        }
        
        data = {}
        for key, query in queries.items():
            data[key] = pd.read_sql(query, self.conn)
        
        return data
    
    def generate_pricing_recommendations(self, margin_data):
        """Générer des recommandations de prix"""
        
        recommendations = []
        
        if margin_data.empty:
            return recommendations
        
        # Produits avec marges faibles
        low_margin_products = margin_data[margin_data['margin_percentage'] < 20]
        
        for _, product in low_margin_products.head(5).iterrows():
            recommendations.append({
                'category': 'pricing',
                'priority': 'high',
                'title': f'🏷️ Optimiser le prix du produit: {product["product_name"][:30]}',
                'description': f'Marge actuelle: {product["margin_percentage"]:.1f}%',
                'action': f'Augmenter le prix de vente de 10-15% pour atteindre une marge de 30%',
                'expected_impact': f'Augmentation de la marge de {30 - product["margin_percentage"]:.1f} points',
                'implementation': 'Facile - Modification dans le catalogue produits'
            })
        
        # Produits avec marges élevées (opportunité de volume)
        high_margin_products = margin_data[margin_data['margin_percentage'] > 50]
        
        for _, product in high_margin_products.head(3).iterrows():
            recommendations.append({
                'category': 'pricing',
                'priority': 'medium',
                'title': f'📈 Augmenter les ventes: {product["product_name"][:30]}',
                'description': f'Marge élevée: {product["margin_percentage"]:.1f}% mais faible volume',
                'action': 'Lancer une promotion ou campagne marketing pour augmenter les ventes',
                'expected_impact': 'Augmentation du volume de ventes de 20-30%',
                'implementation': 'Moyenne - Campagne marketing requise'
            })
        
        return recommendations
    
    def generate_inventory_recommendations(self, inventory_data):
        """Générer des recommandations de gestion des stocks"""
        
        recommendations = []
        
        if inventory_data.empty:
            return recommendations
        
        # Stocks surévalués (faible rotation)
        overstock = inventory_data[inventory_data['turnover_rate'] < 2]
        
        for _, product in overstock.head(5).iterrows():
            recommendations.append({
                'category': 'inventory',
                'priority': 'high',
                'title': f'📦 Stock excessif: {product["product_name"][:30]}',
                'description': f'Taux de rotation: {product["turnover_rate"]:.1f} (objectif > 4)',
                'action': 'Lancer une promotion de déstockage ou réduire les commandes fournisseurs',
                'expected_impact': 'Réduction des coûts de stockage de 15-25%',
                'implementation': 'Moyenne - Promotion et planification requises'
            })
        
        # Risques de rupture
        low_turnover = inventory_data[
            (inventory_data['turnover_rate'] > 8) & 
            (inventory_data['current_stock'] < 50)
        ]
        
        for _, product in low_turnover.head(3).iterrows():
            recommendations.append({
                'category': 'inventory',
                'priority': 'high',
                'title': f'⚠️ Risque de rupture: {product["product_name"][:30]}',
                'description': f'Rotation élevée: {product["turnover_rate"]:.1f} avec stock faible',
                'action': 'Augmenter les commandes fournisseurs ou trouver des alternatives',
                'expected_impact': 'Éviter les pertes de ventes estimées à 10-15%',
                'implementation': 'Urgent - Contact fournisseurs immédiat'
            })
        
        return recommendations
    
    def generate_customer_recommendations(self, customer_data):
        """Générer des recommandations de gestion client"""
        
        recommendations = []
        
        if customer_data.empty:
            return recommendations
        
        # Segmentation pour recommandations
        high_value_customers = customer_data[customer_data['annual_value'] > customer_data['annual_value'].quantile(0.8)]
        
        if len(high_value_customers) > 0:
            recommendations.append({
                'category': 'customer',
                'priority': 'high',
                'title': f'👑 Programme VIP pour {len(high_value_customers)} clients',
                'description': f'Clients avec valeur annuelle > {customer_data["annual_value"].quantile(0.8):.0f} €',
                'action': 'Créer un programme de fidélité avec avantages exclusifs',
                'expected_impact': 'Augmentation de la rétention de 20-30%',
                'implementation': 'Moyenne - Développement programme requis'
            })
        
        # Clients en risque d'attrition
        inactive_threshold = datetime.now() - timedelta(days=90)
        at_risk_customers = customer_data[
            pd.to_datetime(customer_data['last_order']) < inactive_threshold
        ]
        
        if len(at_risk_customers) > len(customer_data) * 0.2:
            recommendations.append({
                'category': 'customer',
                'priority': 'high',
                'title': f'🔄 Campagne de réactivation pour {len(at_risk_customers)} clients',
                'description': 'Clients inactifs depuis plus de 90 jours',
                'action': 'Lancer une campagne email avec offres spéciales de réactivation',
                'expected_impact': 'Réactivation de 15-25% des clients ciblés',
                'implementation': 'Rapide - Email marketing requis'
            })
        
        return recommendations
    
    def generate_llm_recommendations(self, data_summary):
        """Utiliser LLM pour générer des recommandations stratégiques"""
        
        if not self.llm_api_key:
            return []
        
        context = f"""
        Analyse business ERP Distribution:
        - Performance ventes: {data_summary.get('sales_performance', 'stable')}
        - Marge moyenne: {data_summary.get('avg_margin', 0):.1f}%
        - Rotation stocks: {data_summary.get('avg_turnover', 0):.1f}
        - Valeur client moyenne: {data_summary.get('avg_customer_value', 0):.0f} €
        
        Génère 3 recommandations stratégiques actionnables.
        Format JSON avec: category, priority (high/medium/low), title, description, action, expected_impact, implementation
        """
        
        try:
            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Tu es un consultant business expert en retail et distribution.'},
                    {'role': 'user', 'content': context}
                ],
                'temperature': 0.7,
                'max_tokens': 600
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
                
                try:
                    llm_recommendations = json.loads(content)
                    return llm_recommendations if isinstance(llm_recommendations, list) else []
                except:
                    return []
            
        except Exception as e:
            print(f"Erreur LLM: {e}")
            return []
        
        return []
    
    def generate_recommendations_report(self):
        """Générer un rapport complet de recommandations"""
        
        print("🎯 Génération des recommandations stratégiques...")
        
        # Charger les données
        data = self.load_performance_data()
        
        # Résumé pour LLM
        data_summary = {
            'sales_performance': 'croissance' if not data['sales_performance'].empty and data['sales_performance']['ca_mensuel'].iloc[-1] > data['sales_performance']['ca_mensuel'].iloc[-2] else 'stable',
            'avg_margin': data['product_margins']['margin_percentage'].mean() if not data['product_margins'].empty else 0,
            'avg_turnover': data['inventory_turnover']['turnover_rate'].mean() if not data['inventory_turnover'].empty else 0,
            'avg_customer_value': data['customer_lifetime_value']['annual_value'].mean() if not data['customer_lifetime_value'].empty else 0
        }
        
        # Générer les recommandations
        all_recommendations = []
        
        # Recommandations prix
        all_recommendations.extend(self.generate_pricing_recommendations(data['product_margins']))
        
        # Recommandations stocks
        all_recommendations.extend(self.generate_inventory_recommendations(data['inventory_turnover']))
        
        # Recommandations clients
        all_recommendations.extend(self.generate_customer_recommendations(data['customer_lifetime_value']))
        
        # Recommandations LLM
        llm_recommendations = self.generate_llm_recommendations(data_summary)
        all_recommendations.extend(llm_recommendations)
        
        # Trier par priorité
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        all_recommendations.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
        
        # Afficher le rapport
        self.display_recommendations_report(all_recommendations)
        
        # Sauvegarder
        self.save_recommendations_report(all_recommendations)
        
        return all_recommendations
    
    def display_recommendations_report(self, recommendations):
        """Afficher le rapport de recommandations"""
        
        print("\n" + "="*80)
        print("🎯 RAPPORT DE RECOMMANDATIONS STRATÉGIQUES")
        print("="*80)
        
        # Regrouper par catégorie
        categories = {}
        for rec in recommendations:
            if rec['category'] not in categories:
                categories[rec['category']] = []
            categories[rec['category']].append(rec)
        
        category_icons = {
            'pricing': '🏷️',
            'inventory': '📦',
            'customer': '👥',
            'marketing': '📢',
            'operational': '⚙️'
        }
        
        for category, recs in categories.items():
            icon = category_icons.get(category, '📋')
            print(f"\n{icon} {category.upper()} ({len(recs)} recommandations)")
            print("-" * 60)
            
            for i, rec in enumerate(recs, 1):
                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec['priority'], '⚪')
                
                print(f"\n{i}. {rec['title']} {priority_emoji}")
                print(f"   📝 {rec['description']}")
                print(f"   💡 Action: {rec['action']}")
                print(f"   📈 Impact attendu: {rec['expected_impact']}")
                print(f"   🔧 Mise en œuvre: {rec['implementation']}")
        
        print(f"\n✅ Total: {len(recommendations)} recommandations générées")
    
    def save_recommendations_report(self, recommendations):
        """Sauvegarder le rapport de recommandations"""
        
        # Créer un DataFrame
        df = pd.DataFrame(recommendations)
        
        # Sauvegarder en CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'analytics/ai_reporting/recommendations_{timestamp}.csv'
        df.to_csv(filename, index=False)
        
        # Sauvegarder en JSON
        json_filename = f'analytics/ai_reporting/recommendations_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Rapport sauvegardé:")
        print(f"  📄 CSV: {filename}")
        print(f"  📄 JSON: {json_filename}")
    
    def close(self):
        """Fermer la connexion"""
        self.conn.close()

def main():
    """Fonction principale"""
    print("🚀 Lancement du moteur de recommandations IA...")
    
    engine = RecommendationEngine()
    
    try:
        recommendations = engine.generate_recommendations_report()
        print(f"\n🎯 {len(recommendations)} recommandations stratégiques générées!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        engine.close()

if __name__ == "__main__":
    main()

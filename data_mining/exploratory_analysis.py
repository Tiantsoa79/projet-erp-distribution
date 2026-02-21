"""
Analyse exploratoire des données du Data Warehouse

Exploration complète des données pour comprendre les tendances,
patterns et insights business.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class ExploratoryAnalysis:
    def __init__(self, connection):
        self.conn = connection
        self.results = {}
        
    def load_data(self, quick=False):
        """Charger les données pour l'analyse exploratoire"""
        
        # Limiter les données en mode quick
        limit_clause = "LIMIT 10000" if quick else ""
        
        queries = {
            'orders_summary': f"""
                SELECT 
                    fol.order_id,
                    fol.sales_amount,
                    fol.order_date_key,
                    fol.customer_key,
                    fol.geography_key,
                    dd.full_date,
                    dd.month_name,
                    dd.year_number,
                    dd.is_weekend,
                    dc.customer_name,
                    dg.country,
                    dg.region,
                    dg.city
                FROM dwh.fact_sales_order_line fol
                JOIN dwh.dim_date dd ON fol.order_date_key = dd.date_key
                JOIN dwh.dim_customer dc ON fol.customer_key = dc.customer_key
                JOIN dwh.dim_geography dg ON fol.geography_key = dg.geography_key
                {limit_clause}
            """,
            
            'products_analysis': f"""
                SELECT 
                    dp.product_name,
                    dp.category,
                    dp.sub_category,
                    SUM(fol.quantity) AS total_quantity,
                    SUM(fol.sales_amount) AS total_sales,
                    AVG(fol.unit_price_amount) AS avg_price,
                    COUNT(DISTINCT fol.customer_key) AS unique_customers,
                    COUNT(*) AS transactions_count
                FROM dwh.fact_sales_order_line fol
                JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
                GROUP BY dp.product_name, dp.category, dp.sub_category
                {limit_clause}
            """,
            
            'temporal_patterns': f"""
                SELECT 
                    dd.full_date,
                    dd.year_number,
                    dd.month_name,
                    dd.day_of_month AS day_of_week,
                    dd.is_weekend,
                    COUNT(DISTINCT fol.order_id) AS daily_orders,
                    SUM(fol.sales_amount) AS daily_sales,
                    COUNT(DISTINCT fol.customer_key) AS daily_customers,
                    AVG(fol.sales_amount) AS avg_order_value
                FROM dwh.fact_sales_order_line fol
                JOIN dwh.dim_date dd ON fol.order_date_key = dd.date_key
                GROUP BY dd.full_date, dd.year_number, dd.month_name, dd.day_of_month, dd.is_weekend
                ORDER BY dd.full_date
                {limit_clause}
            """
        }
        
        data = {}
        for name, query in queries.items():
            data[name] = pd.read_sql(query, self.conn)
            
        return data
    
    def analyze_summary_statistics(self, data):
        """Analyser les statistiques descriptives"""
        
        summary = {}
        
        # Statistiques des commandes
        orders = data['orders_summary']
        summary['orders'] = {
            'total_records': len(orders),
            'total_sales': orders['sales_amount'].sum(),
            'avg_order_value': orders['sales_amount'].mean(),
            'median_order_value': orders['sales_amount'].median(),
            'unique_customers': orders['customer_name'].nunique(),
            'unique_regions': orders['region'].nunique(),
            'weekend_orders': len(orders[orders['is_weekend']]),
            'weekday_orders': len(orders[~orders['is_weekend']])
        }
        
        # Statistiques produits
        products = data['products_analysis']
        summary['products'] = {
            'unique_products': len(products),
            'unique_categories': products['category'].nunique(),
            'total_quantity_sold': products['total_quantity'].sum(),
            'avg_product_price': products['avg_price'].mean(),
            'top_category': products.groupby('category')['total_sales'].sum().idxmax()
        }
        
        # Patterns temporels
        temporal = data['temporal_patterns']
        summary['temporal'] = {
            'date_range': f"{temporal['full_date'].min()} à {temporal['full_date'].max()}",
            'total_days': len(temporal),
            'avg_daily_orders': temporal['daily_orders'].mean(),
            'avg_daily_sales': temporal['daily_sales'].mean(),
            'best_day_sales': temporal.loc[temporal['daily_sales'].idxmax(), 'full_date'].strftime('%Y-%m-%d'),
            'weekend_vs_weekday_ratio': temporal[temporal['is_weekend']]['daily_sales'].mean() / temporal[~temporal['is_weekend']]['daily_sales'].mean()
        }
        
        return summary
    
    def generate_visualizations(self, data):
        """Générer les visualisations"""
        
        plots = {}
        
        # 1. Distribution des montants de commandes
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        sns.histplot(data['orders_summary']['sales_amount'], bins=50, kde=True)
        plt.title('Distribution des montants de commandes')
        plt.xlabel('Montant (€)')
        
        plt.subplot(1, 2, 2)
        sns.boxplot(y=data['orders_summary']['sales_amount'])
        plt.title('Boxplot - Montants de commandes')
        plt.ylabel('Montant (€)')
        
        plt.tight_layout()
        plot_path = 'results/plots/order_amounts_distribution.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['order_amounts'] = plot_path
        
        # 2. Ventes par région
        plt.figure(figsize=(12, 6))
        region_sales = data['orders_summary'].groupby('region')['sales_amount'].sum().sort_values(ascending=False)
        sns.barplot(x=region_sales.values, y=region_sales.index)
        plt.title('Ventes totales par région')
        plt.xlabel('Montant total (€)')
        plt.ylabel('Région')
        
        plt.tight_layout()
        plot_path = 'results/plots/sales_by_region.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['regional_sales'] = plot_path
        
        # 3. Top 10 produits
        plt.figure(figsize=(12, 8))
        top_products = data['products_analysis'].nlargest(10, 'total_sales')
        sns.barplot(data=top_products, x='total_sales', y='product_name')
        plt.title('Top 10 produits par ventes totales')
        plt.xlabel('Ventes totales (€)')
        plt.ylabel('Produit')
        
        plt.tight_layout()
        plot_path = 'results/plots/top_products.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['top_products'] = plot_path
        
        # 4. Patterns temporels
        plt.figure(figsize=(15, 10))
        
        plt.subplot(2, 2, 1)
        temporal = data['temporal_patterns']
        plt.plot(temporal['full_date'], temporal['daily_sales'])
        plt.title('Évolution des ventes quotidiennes')
        plt.xlabel('Date')
        plt.ylabel('Ventes (€)')
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 2)
        monthly_sales = temporal.groupby('month_name')['daily_sales'].mean()
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        monthly_sales = monthly_sales.reindex(month_order)
        sns.barplot(x=monthly_sales.index, y=monthly_sales.values)
        plt.title('Ventes moyennes par mois')
        plt.xlabel('Mois')
        plt.ylabel('Ventes moyennes (€)')
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 3)
        weekday_sales = temporal.groupby('day_of_week')['daily_sales'].mean()
        sns.barplot(x=weekday_sales.index, y=weekday_sales.values)
        plt.title('Ventes moyennes par jour de la semaine')
        plt.xlabel('Jour de la semaine')
        plt.ylabel('Ventes moyennes (€)')
        
        plt.subplot(2, 2, 4)
        weekend_vs_weekday = pd.DataFrame({
            'Semaine': temporal[~temporal['is_weekend']]['daily_sales'],
            'Weekend': temporal[temporal['is_weekend']]['daily_sales']
        })
        sns.boxplot(data=weekend_vs_weekday)
        plt.title('Distribution ventes : Semaine vs Weekend')
        plt.ylabel('Ventes (€)')
        
        plt.tight_layout()
        plot_path = 'results/plots/temporal_patterns.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['temporal_patterns'] = plot_path
        
        return plots
    
    def analyze_correlations(self, data):
        """Analyser les corrélations"""
        
        # Préparer les données pour l'analyse de corrélation
        orders = data['orders_summary']
        
        # Agréger par client pour analyser les corrélations
        customer_stats = orders.groupby('customer_name').agg({
            'sales_amount': ['sum', 'mean', 'count'],
            'is_weekend': ['sum', 'count']
        }).round(2)
        
        customer_stats.columns = ['total_spent', 'avg_order', 'order_count', 'weekend_orders', 'total_orders']
        customer_stats['weekend_ratio'] = customer_stats['weekend_orders'] / customer_stats['total_orders']
        
        # Matrice de corrélation
        correlation_matrix = customer_stats[['total_spent', 'avg_order', 'order_count', 'weekend_ratio']].corr()
        
        # Visualisation
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, 
                   square=True, fmt='.2f')
        plt.title('Matrice de corrélation - Métriques clients')
        
        plt.tight_layout()
        plot_path = 'results/plots/correlation_matrix.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'correlation_matrix': correlation_matrix,
            'plot_path': plot_path
        }
    
    def run(self, quick=False):
        """Exécuter l'analyse exploratoire complète"""
        
        print("Chargement des données...")
        data = self.load_data(quick)
        
        print("Analyse des statistiques descriptives...")
        summary = self.analyze_summary_statistics(data)
        
        print("Génération des visualisations...")
        plots = self.generate_visualizations(data)
        
        print("Analyse des corrélations...")
        correlations = self.analyze_correlations(data)
        
        # Exporter les données
        data['orders_summary'].to_csv('results/data/orders_summary.csv', index=False)
        data['products_analysis'].to_csv('results/data/products_analysis.csv', index=False)
        data['temporal_patterns'].to_csv('results/data/temporal_patterns.csv', index=False)
        
        self.results = {
            'summary': summary,
            'plots': plots,
            'correlations': correlations,
            'data_exported': True
        }
        
        return self.results

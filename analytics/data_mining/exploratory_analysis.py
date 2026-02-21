"""
Analyse exploratoire des données du Data Warehouse

Exploration complète des données pour comprendre les tendances,
patterns et insights business.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

def load_overview_data():
    """Charger les données pour l'analyse exploratoire"""
    
    queries = {
        'orders_summary': """
            SELECT 
                fo.order_key,
                fo.total_amount,
                fo.order_date_key,
                fo.customer_key,
                fo.ship_geography_key,
                dd.full_date,
                dd.month_name,
                dd.year_number,
                dd.is_weekend,
                dc.customer_name,
                dg.country,
                dg.region,
                dg.city
            FROM dwh.fact_orders fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN dwh.dim_customer dc ON fo.customer_key = dc.customer_key
            JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
            WHERE fo.total_amount > 0
        """,
        
        'products_summary': """
            SELECT 
                dp.product_key,
                dp.product_name,
                dp.product_category,
                dp.unit_price,
                ds.supplier_name,
                COUNT(fol.order_line_key) AS nb_ventes,
                SUM(fol.quantity) AS quantite_totale,
                SUM(fol.line_amount) AS ca_total,
                AVG(fol.unit_price) AS prix_vente_moyen
            FROM dwh.dim_product dp
            JOIN dwh.dim_supplier ds ON dp.supplier_key = ds.supplier_key
            LEFT JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
            GROUP BY dp.product_key, dp.product_name, dp.product_category, 
                     dp.unit_price, ds.supplier_name
        """,
        
        'customers_summary': """
            SELECT 
                dc.customer_key,
                dc.customer_name,
                dc.email,
                COUNT(DISTINCT fo.order_key) AS nb_commandes,
                SUM(fo.total_amount) AS ca_total,
                AVG(fo.total_amount) AS panier_moyen,
                MIN(dd.full_date) AS premiere_commande,
                MAX(dd.full_date) AS derniere_commande,
                COUNT(DISTINCT dg.country) AS nb_pays_livraison
            FROM dwh.dim_customer dc
            LEFT JOIN dwh.fact_orders fo ON dc.customer_key = fo.customer_key
            LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            LEFT JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
            GROUP BY dc.customer_key, dc.customer_name, dc.email
        """,
        
        'time_series': """
            SELECT 
                dd.full_date,
                dd.month_name,
                dd.year_number,
                dd.quarter_number,
                COUNT(DISTINCT fo.order_key) AS nb_commandes,
                SUM(fo.total_amount) AS ca_total,
                AVG(fo.total_amount) AS panier_moyen,
                COUNT(DISTINCT fo.customer_key) AS nb_clients_actifs
            FROM dwh.fact_orders fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            GROUP BY dd.full_date, dd.month_name, dd.year_number, dd.quarter_number
            ORDER BY dd.full_date
        """
    }
    
    conn = get_connection()
    data = {}
    for key, query in queries.items():
        data[key] = pd.read_sql(query, conn)
    conn.close()
    
    return data

def analyze_sales_trends(data):
    """Analyser les tendances des ventes"""
    
    print("📈 ANALYSE DES TENDANCES DE VENTES")
    print("=" * 50)
    
    df = data['time_series']
    
    # Statistiques générales
    total_ca = df['ca_total'].sum()
    total_commandes = df['nb_commandes'].sum()
    panier_moyen_global = total_ca / total_commandes
    
    print(f"💰 Chiffre d'affaires total: {total_ca:,.0f} €")
    print(f"📦 Nombre total de commandes: {total_commandes:,}")
    print(f"🛒 Panier moyen global: {panier_moyen_global:.2f} €")
    print(f"👥 Nombre total de clients actifs: {df['nb_clients_actifs'].max():,}")
    print()
    
    # Analyse mensuelle
    monthly_stats = df.groupby(['year_number', 'month_name']).agg({
        'ca_total': 'sum',
        'nb_commandes': 'sum',
        'nb_clients_actifs': 'sum'
    }).reset_index()
    
    print("📅 TOP 10 MEILLEURS MOIS:")
    top_months = monthly_stats.nlargest(10, 'ca_total')
    for idx, row in top_months.iterrows():
        print(f"  {idx+1}. {row['month_name']} {row['year_number']}: "
              f"{row['ca_total']:,.0f} € ({row['nb_commandes']} commandes)")
    
    return monthly_stats

def analyze_product_performance(data):
    """Analyser la performance des produits"""
    
    print("\n🏭 ANALYSE DE LA PERFORMANCE PRODUITS")
    print("=" * 50)
    
    df = data['products_summary']
    
    # Top produits par CA
    print("💎 TOP 10 PRODUITS PAR CA:")
    top_products = df.nlargest(10, 'ca_total')[['product_name', 'product_category', 'ca_total', 'nb_ventes']]
    for idx, row in top_products.iterrows():
        print(f"  {idx+1}. {row['product_name']}: {row['ca_total']:,.0f} € "
              f"({row['nb_ventes']} ventes)")
    
    # Analyse par catégorie
    print("\n📊 PERFORMANCE PAR CATÉGORIE:")
    category_stats = df.groupby('product_category').agg({
        'ca_total': 'sum',
        'nb_ventes': 'sum',
        'product_key': 'count'
    }).sort_values('ca_total', ascending=False)
    
    for category, stats in category_stats.iterrows():
        print(f"  • {category}: {stats['ca_total']:,.0f} € "
              f"({stats['nb_ventes']} ventes, {stats['product_key']} produits)")
    
    return category_stats

def analyze_customer_behavior(data):
    """Analyser le comportement client"""
    
    print("\n👥 ANALYSE DU COMPORTEMENT CLIENT")
    print("=" * 50)
    
    df = data['customers_summary']
    
    # Statistiques clients
    active_customers = df[df['nb_commandes'] > 0]
    print(f"📊 Nombre total de clients: {len(df):,}")
    print(f"🛒 Clients actifs: {len(active_customers):,} ({len(active_customers)/len(df)*100:.1f}%)")
    print(f"💰 Panier moyen: {active_customers['panier_moyen'].mean():.2f} €")
    print(f"📦 Commandes moyennes par client: {active_customers['nb_commandes'].mean():.1f}")
    print()
    
    # Top clients
    print("💎 TOP 10 CLIENTS PAR CA:")
    top_customers = active_customers.nlargest(10, 'ca_total')[['customer_name', 'ca_total', 'nb_commandes', 'panier_moyen']]
    for idx, row in top_customers.iterrows():
        print(f"  {idx+1}. {row['customer_name']}: {row['ca_total']:,.0f} € "
              f"({row['nb_commandes']} commandes, panier {row['panier_moyen']:.0f} €)")
    
    # Segmentation simple
    def segment_customer(row):
        if row['ca_total'] > active_customers['ca_total'].quantile(0.8):
            return 'VIP'
        elif row['ca_total'] > active_customers['ca_total'].quantile(0.6):
            return 'Premium'
        elif row['ca_total'] > active_customers['ca_total'].quantile(0.4):
            return 'Standard'
        else:
            return 'Occasionnel'
    
    active_customers['segment'] = active_customers.apply(segment_customer, axis=1)
    
    print("\n🎯 RÉPARTITION PAR SEGMENT:")
    segment_counts = active_customers['segment'].value_counts()
    for segment, count in segment_counts.items():
        print(f"  • {segment}: {count} clients ({count/len(active_customers)*100:.1f}%)")
    
    return active_customers

def analyze_geographical_distribution(data):
    """Analyser la distribution géographique"""
    
    print("\n🌍 ANALYSE GÉOGRAPHIQUE")
    print("=" * 50)
    
    df = data['orders_summary']
    
    # Par pays
    country_stats = df.groupby('country').agg({
        'order_key': 'count',
        'total_amount': 'sum'
    }).sort_values('total_amount', ascending=False)
    
    print("🌎 TOP 10 PAYS PAR CA:")
    for idx, (country, stats) in enumerate(country_stats.head(10).iterrows()):
        print(f"  {idx+1}. {country}: {stats['total_amount']:,.0f} € "
              f"({stats['order_key']} commandes)")
    
    # Par ville
    city_stats = df.groupby(['country', 'city']).agg({
        'order_key': 'count',
        'total_amount': 'sum'
    }).sort_values('total_amount', ascending=False)
    
    print("\n🏙️ TOP 10 VILLES PAR CA:")
    for idx, (country_city, stats) in enumerate(city_stats.head(10).iterrows()):
        country, city = country_city
        print(f"  {idx+1}. {city}, {country}: {stats['total_amount']:,.0f} € "
              f"({stats['order_key']} commandes)")
    
    return country_stats, city_stats

def create_exploratory_visualizations(data):
    """Créer des visualisations pour l'analyse exploratoire"""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. Évolution du CA dans le temps
    time_df = data['time_series']
    axes[0, 0].plot(pd.to_datetime(time_df['full_date']), time_df['ca_total'])
    axes[0, 0].set_title('Évolution du CA dans le temps')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('CA (€)')
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. Distribution des montants de commandes
    orders_df = data['orders_summary']
    axes[0, 1].hist(orders_df['total_amount'], bins=50, alpha=0.7)
    axes[0, 1].set_title('Distribution des montants de commandes')
    axes[0, 1].set_xlabel('Montant (€)')
    axes[0, 1].set_ylabel('Fréquence')
    
    # 3. CA par pays
    country_stats = orders_df.groupby('country')['total_amount'].sum().sort_values(ascending=False).head(10)
    axes[0, 2].bar(range(len(country_stats)), country_stats.values)
    axes[0, 2].set_title('Top 10 pays par CA')
    axes[0, 2].set_xlabel('Pays')
    axes[0, 2].set_ylabel('CA (€)')
    axes[0, 2].set_xticks(range(len(country_stats)))
    axes[0, 2].set_xticklabels(country_stats.index, rotation=45)
    
    # 4. Top produits par CA
    product_df = data['products_summary']
    top_products = product_df.nlargest(10, 'ca_total')
    axes[1, 0].barh(range(len(top_products)), top_products['ca_total'])
    axes[1, 0].set_title('Top 10 produits par CA')
    axes[1, 0].set_xlabel('CA (€)')
    axes[1, 0].set_yticks(range(len(top_products)))
    axes[1, 0].set_yticklabels(top_products['product_name'].str[:30])  # Limiter la longueur
    
    # 5. Distribution du nombre de commandes par client
    customer_df = data['customers_summary']
    active_customers = customer_df[customer_df['nb_commandes'] > 0]
    axes[1, 1].hist(active_customers['nb_commandes'], bins=30, alpha=0.7)
    axes[1, 1].set_title('Distribution commandes par client')
    axes[1, 1].set_xlabel('Nombre de commandes')
    axes[1, 1].set_ylabel('Nombre de clients')
    
    # 6. CA par jour de la semaine
    orders_df['day_of_week'] = pd.to_datetime(orders_df['full_date']).dt.day_name()
    weekday_stats = orders_df.groupby('day_of_week')['total_amount'].sum()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_stats = weekday_stats.reindex(weekday_order)
    
    axes[1, 2].bar(range(len(weekday_stats)), weekday_stats.values)
    axes[1, 2].set_title('CA par jour de la semaine')
    axes[1, 2].set_xlabel('Jour de la semaine')
    axes[1, 2].set_ylabel('CA (€)')
    axes[1, 2].set_xticks(range(len(weekday_stats)))
    axes[1, 2].set_xticklabels([d[:3] for d in weekday_stats.index])
    
    plt.tight_layout()
    plt.savefig('analytics/data_mining/exploratory_analysis.png', dpi=150, bbox_inches='tight')
    plt.show()

def save_exploratory_results(data):
    """Sauvegarder les résultats de l'analyse exploratoire"""
    
    # Sauvegarder les dataframes
    for key, df in data.items():
        df.to_csv(f'analytics/data_mining/{key}_analysis.csv', index=False)
    
    print(f"\n💾 Résultats sauvegardés dans analytics/data_mining/")
    print("  • orders_summary_analysis.csv")
    print("  • products_summary_analysis.csv")
    print("  • customers_summary_analysis.csv")
    print("  • time_series_analysis.csv")

def main():
    """Fonction principale d'analyse exploratoire"""
    print("🚀 Lancement de l'analyse exploratoire...")
    
    # Charger les données
    data = load_overview_data()
    print(f"📥 Données chargées: {len(data['orders_summary']):,} commandes, "
          f"{len(data['products_summary']):,} produits, {len(data['customers_summary']):,} clients")
    
    # Analyses
    analyze_sales_trends(data)
    analyze_product_performance(data)
    analyze_customer_behavior(data)
    analyze_geographical_distribution(data)
    
    # Visualisations
    create_exploratory_visualizations(data)
    
    # Sauvegarder
    save_exploratory_results(data)
    
    print("\n✅ Analyse exploratoire terminée avec succès!")

if __name__ == "__main__":
    main()

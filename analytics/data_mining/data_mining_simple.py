"""
Data Mining Simplifié - Analyse des Clients
Script corrigé pour le Data Warehouse actuel
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
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

def load_customer_data():
    """Charger les données clients pour le clustering"""
    query = """
    SELECT 
        dc.customer_key,
        dc.customer_name,
        COUNT(DISTINCT fo.order_id) as nb_commandes,
        SUM(fo.sales_amount) as ca_total,
        AVG(fo.sales_amount) as panier_moyen,
        MIN(dd.full_date) as premiere_commande,
        MAX(dd.full_date) as derniere_commande,
        COUNT(DISTINCT dp.category) as nb_categories
    FROM dwh.dim_customer dc
    LEFT JOIN dwh.fact_sales_order_line fo ON dc.customer_key = fo.customer_key
    LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
    LEFT JOIN dwh.dim_product dp ON fo.product_key = dp.product_key
    WHERE fo.order_date_key IS NOT NULL
    GROUP BY dc.customer_key, dc.customer_name
    ORDER BY ca_total DESC
    """
    
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def perform_rfm_analysis(df):
    """Analyse RFM simplifiée"""
    print("📊 ANALYSE RFM - SEGMENTATION CLIENTS")
    print("=" * 50)
    
    # Date de référence
    max_date = df['derniere_commande'].max()
    
    # Calcul RFM
    rfm = df.groupby('customer_key').agg({
        'derniere_commande': lambda x: (max_date - x.max()).days if pd.notna(x.max()) else 999,
        'nb_commandes': 'first',
        'ca_total': 'first'
    }).reset_index()
    
    rfm.columns = ['customer_key', 'recency', 'frequency', 'monetary']
    
    # Scores RFM (1-5)
    rfm['R_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm['M_score'] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5])
    
    # Segmentation
    def get_segment(row):
        r_total = row['R_score'] + row['F_score'] + row['M_score']
        if r_total >= 13:
            return 'Champions'
        elif row['R_score'] >= 4 and row['F_score'] >= 3:
            return 'Clients Fidèles'
        elif row['R_score'] >= 3 and row['M_score'] >= 3:
            return 'Clients Potentiels'
        elif row['R_score'] >= 4:
            return 'Nouveaux Clients'
        elif row['R_score'] <= 2 and row['F_score'] <= 2:
            return 'Clients à Risque'
        elif row['R_score'] <= 2:
            return 'Clients Perdus'
        else:
            return 'Autres'
    
    rfm['segment'] = rfm.apply(get_segment, axis=1)
    
    # Ajouter infos client
    customer_info = df[['customer_key', 'customer_name']].drop_duplicates()
    rfm = rfm.merge(customer_info, on='customer_key')
    
    # Statistiques
    print(f"📈 Nombre total de clients: {len(rfm):,}")
    print(f"💰 Panier moyen: {rfm['monetary'].mean():.2f} €")
    print(f"🔄 Fréquence moyenne: {rfm['frequency'].mean():.1f} commandes")
    print(f"📅 Récence moyenne: {rfm['recency'].mean():.1f} jours")
    print()
    
    # Répartition par segment
    print("🎯 RÉPARTITION PAR SEGMENT:")
    segment_counts = rfm['segment'].value_counts()
    segment_percentages = (segment_counts / len(rfm) * 100).round(1)
    
    for segment, count in segment_counts.items():
        print(f"  • {segment}: {count} clients ({segment_percentages[segment]}%)")
    
    return rfm

def perform_kmeans_clustering(df):
    """Clustering K-Means simplifié"""
    print("\n🔍 CLUSTERING K-MEANS")
    print("=" * 30)
    
    # Préparation des données
    features = df[['nb_commandes', 'ca_total', 'panier_moyen', 'nb_categories']].fillna(0)
    
    # Standardisation
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # K-Means avec 4 clusters
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(features_scaled)
    
    # Ajouter les clusters au DataFrame
    df['cluster'] = clusters
    
    # Analyse des clusters
    print("📊 ANALYSE DES CLUSTERS:")
    for i in range(4):
        cluster_data = df[df['cluster'] == i]
        print(f"\n  Cluster {i} ({len(cluster_data)} clients):")
        print(f"    • CA moyen: {cluster_data['ca_total'].mean():.0f} €")
        print(f"    • Commandes moyennes: {cluster_data['nb_commandes'].mean():.1f}")
        print(f"    • Panier moyen: {cluster_data['panier_moyen'].mean():.0f} €")
        print(f"    • Catégories moyennes: {cluster_data['nb_categories'].mean():.1f}")
    
    return df

def generate_insights(df, rfm):
    """Générer des insights business"""
    print("\n💡 INSIGHTS BUSINESS")
    print("=" * 30)
    
    # Top clients
    top_clients = df.nlargest(5, 'ca_total')
    print("\n🏆 TOP 5 CLIENTS PAR CA:")
    for idx, client in top_clients.iterrows():
        print(f"  {idx+1}. {client['customer_name']}: {client['ca_total']:,.0f} €")
    
    # Segments à risque
    at_risk = rfm[rfm['segment'].isin(['Clients à Risque', 'Clients Perdus'])]
    print(f"\n⚠️  CLIENTS À SURVEILLER: {len(at_risk)} clients ({len(at_risk)/len(rfm)*100:.1f}%)")
    
    # Opportunités
    potential = rfm[rfm['segment'] == 'Clients Potentiels']
    print(f"🎯 CLIENTS POTENTIELS: {len(potential)} clients ({len(potential)/len(rfm)*100:.1f}%)")

def main():
    """Fonction principale"""
    print("🚀 Lancement du Data Mining Simplifié...")
    
    # Charger les données
    df = load_customer_data()
    print(f"📥 {len(df):,} clients chargés")
    
    # Analyse RFM
    rfm = perform_rfm_analysis(df)
    
    # Clustering K-Means
    df_with_clusters = perform_kmeans_clustering(df)
    
    # Générer insights
    generate_insights(df_with_clusters, rfm)
    
    # Sauvegarder résultats
    rfm.to_csv('analytics/data_mining/rfm_results_simple.csv', index=False)
    df_with_clusters.to_csv('analytics/data_mining/clustering_results_simple.csv', index=False)
    
    print(f"\n💾 Résultats sauvegardés:")
    print(f"  • analytics/data_mining/rfm_results_simple.csv")
    print(f"  • analytics/data_mining/clustering_results_simple.csv")
    
    print("\n✅ Data Mining terminé avec succès!")

if __name__ == "__main__":
    main()

"""
Segmentation RFM (Recency, Frequency, Monetary)

Analyse comportementale des clients basée sur:
- Recency: Dernier achat
- Frequency: Nombre d'achats
- Monetary: Montant total dépensé
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
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

def load_customer_data():
    """Charger les données clients pour l'analyse RFM"""
    query = """
    SELECT 
        dc.customer_key,
        dc.customer_name,
        dc.email,
        fo.order_id,
        fo.order_date_key,
        fo.sales_amount,
        dd.full_date
    FROM dwh.fact_sales_order_line fo
    JOIN dwh.dim_customer dc ON fo.customer_key = dc.customer_key
    JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
    WHERE fo.order_date_key IS NOT NULL
    ORDER BY dc.customer_key, dd.full_date
    """
    
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def calculate_rfm_scores(df):
    """Calculer les scores RFM pour chaque client"""
    
    # Date de référence pour le calcul de récence
    max_date = df['full_date'].max()
    
    # Calcul RFM
    rfm = df.groupby('customer_key').agg({
        'full_date': lambda x: (max_date - x.max()).days,  # Recency
        'order_id': 'count',  # Frequency
        'sales_amount': 'sum'  # Monetary
    }).reset_index()
    
    rfm.columns = ['customer_key', 'recency', 'frequency', 'monetary']
    
    # Ajouter les informations client
    customer_info = df[['customer_key', 'customer_name', 'email']].drop_duplicates()
    rfm = rfm.merge(customer_info, on='customer_key')
    
    # Calcul des scores RFM (1-5, 5 étant le meilleur)
    rfm['R_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm['M_score'] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5])
    
    # Score RFM combiné
    rfm['RFM_score'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str) + rfm['M_score'].astype(str)
    rfm['RFM_total'] = rfm['R_score'].astype(int) + rfm['F_score'].astype(int) + rfm['M_score'].astype(int)
    
    return rfm

def segment_customers(rfm):
    """Segmenter les clients selon les scores RFM"""
    
    def get_segment(row):
        if row['RFM_total'] >= 13:
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
    return rfm

def generate_rfm_report(rfm):
    """Générer un rapport d'analyse RFM"""
    
    print("📊 ANALYSE RFM - SEGMENTATION CLIENTS")
    print("=" * 50)
    
    # Statistiques générales
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
    print()
    
    # Top 10 clients par valeur
    print("💎 TOP 10 CLIENTS PAR VALEUR:")
    top_clients = rfm.nlargest(10, 'monetary')[['customer_name', 'monetary', 'frequency', 'recency']]
    for idx, client in top_clients.iterrows():
        print(f"  {idx+1}. {client['customer_name']}: {client['monetary']:,.0f} € "
              f"({client['frequency']} commandes, il y a {client['recency']:.0f} jours)")
    
    return rfm

def save_results(rfm):
    """Sauvegarder les résultats"""
    
    # Sauvegarder en CSV
    rfm.to_csv('analytics/data_mining/rfm_results.csv', index=False)
    print(f"\n💾 Résultats sauvegardés dans analytics/data_mining/rfm_results.csv")
    
    # Statistiques par segment
    segment_stats = rfm.groupby('segment').agg({
        'customer_key': 'count',
        'monetary': ['sum', 'mean'],
        'frequency': 'mean',
        'recency': 'mean'
    }).round(2)
    
    segment_stats.columns = ['nb_clients', 'ca_total', 'panier_moyen', 'frequence_moyenne', 'recence_moyenne']
    segment_stats.to_csv('analytics/data_mining/rfm_segment_stats.csv')
    print(f"📊 Statistiques par segment sauvegardées dans analytics/data_mining/rfm_segment_stats.csv")

def main():
    """Fonction principale d'analyse RFM"""
    print("🚀 Lancement de l'analyse RFM...")
    
    # Charger les données
    df = load_customer_data()
    print(f"📥 {len(df):,} lignes de commandes chargées")
    
    # Calculer RFM
    rfm = calculate_rfm_scores(df)
    print("📊 Scores RFM calculés")
    
    # Segmenter
    rfm = segment_customers(rfm)
    print("🎯 Segmentation effectuée")
    
    # Générer rapport
    rfm = generate_rfm_report(rfm)
    
    # Sauvegarder
    save_results(rfm)
    
    print("\n✅ Analyse RFM terminée avec succès!")

if __name__ == "__main__":
    main()

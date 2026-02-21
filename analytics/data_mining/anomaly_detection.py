"""
Détection d'anomalies dans les données de ventes

Identifie les transactions et comportements anormaux qui pourraient
indiquer des fraudes, des erreurs système ou des opportunités.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
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

def load_transaction_data():
    """Charger les données de transactions pour la détection d'anomalies"""
    
    query = """
    SELECT 
        fo.order_key,
        fo.order_date_key,
        fo.total_amount,
        fo.customer_key,
        dc.customer_name,
        fo.ship_geography_key,
        dg.country,
        dg.city,
        COUNT(fol.order_line_key) AS nb_lignes,
        SUM(fol.quantity) AS quantite_totale,
        AVG(fol.unit_price) AS prix_moyen_unitaire,
        fo.created_date_key,
        dd.full_date AS order_date
    FROM dwh.fact_orders fo
    JOIN dwh.dim_customer dc ON fo.customer_key = dc.customer_key
    JOIN dwh.dim_geography dg ON fo.ship_geography_key = dg.geography_key
    JOIN dwh.fact_order_lines fol ON fo.order_key = fol.order_key
    JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
    WHERE fo.total_amount > 0
    GROUP BY fo.order_key, fo.order_date_key, fo.total_amount, fo.customer_key, 
             dc.customer_name, fo.ship_geography_key, dg.country, dg.city,
             fo.created_date_key, dd.full_date
    ORDER BY fo.order_date_key
    """
    
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def detect_amount_anomalies(df):
    """Détecter les anomalies basées sur les montants"""
    
    print("🔍 Détection d'anomalies sur les montants...")
    
    # Caractéristiques pour l'analyse
    features = df[['total_amount', 'nb_lignes', 'quantite_totale', 'prix_moyen_unitaire']].copy()
    
    # Gérer les valeurs extrêmes
    for col in features.columns:
        Q1 = features[col].quantile(0.01)
        Q3 = features[col].quantile(0.99)
        features[col] = features[col].clip(Q1, Q3)
    
    # Standardisation
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    anomaly_labels = iso_forest.fit_predict(features_scaled)
    
    # Ajouter les labels au dataframe
    df['amount_anomaly'] = anomaly_labels
    df['amount_anomaly_score'] = iso_forest.decision_function(features_scaled)
    
    # Statistiques des anomalies
    anomalies = df[df['amount_anomaly'] == -1]
    print(f"🚨 {len(anomalies)} transactions anormales détectées ({len(anomalies)/len(df)*100:.1f}%)")
    
    return df, anomalies

def detect_customer_behavior_anomalies(df):
    """Détecter les anomalies de comportement client"""
    
    print("🔍 Détection d'anomalies de comportement client...")
    
    # Statistiques par client
    customer_stats = df.groupby('customer_key').agg({
        'total_amount': ['sum', 'mean', 'std', 'count'],
        'nb_lignes': 'mean',
        'quantite_totale': 'mean'
    }).round(2)
    
    customer_stats.columns = ['ca_total', 'panier_moyen', 'panier_std', 'nb_commandes', 'lignes_moyennes', 'quantite_moyenne']
    
    # Détection d'anomalies basées sur le comportement
    customer_features = customer_stats[['ca_total', 'panier_moyen', 'nb_commandes']].copy()
    
    # Gérer les valeurs manquantes
    customer_features = customer_features.fillna(customer_features.mean())
    
    # Standardisation
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(customer_features)
    
    # Isolation Forest
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    anomaly_labels = iso_forest.fit_predict(features_scaled)
    
    customer_stats['behavior_anomaly'] = anomaly_labels
    customer_stats['anomaly_score'] = iso_forest.decision_function(features_scaled)
    
    # Clients avec comportement anormal
    anomalous_customers = customer_stats[customer_stats['behavior_anomaly'] == -1]
    print(f"🚨 {len(anomalous_customers)} clients avec comportement anormal ({len(anomalous_customers)/len(customer_stats)*100:.1f}%)")
    
    return customer_stats, anomalous_customers

def detect_temporal_anomalies(df):
    """Détecter les anomalies temporelles"""
    
    print("🔍 Détection d'anomalies temporelles...")
    
    # Agrégation par jour
    daily_stats = df.groupby('order_date').agg({
        'total_amount': 'sum',
        'order_key': 'count'
    }).reset_index()
    
    daily_stats.columns = ['date', 'ca_jour', 'nb_commandes_jour']
    
    # Détection d'anomalies sur le CA journalier
    ca_values = daily_stats['ca_jour'].values.reshape(-1, 1)
    scaler = StandardScaler()
    ca_scaled = scaler.fit_transform(ca_values)
    
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    temporal_anomalies = iso_forest.fit_predict(ca_scaled)
    
    daily_stats['temporal_anomaly'] = temporal_anomalies
    daily_stats['anomaly_score'] = iso_forest.decision_function(ca_scaled)
    
    anomalous_days = daily_stats[daily_stats['temporal_anomaly'] == -1]
    print(f"🚨 {len(anomalous_days)} jours avec ventes anormales")
    
    return daily_stats, anomalous_days

def generate_anomaly_report(df, anomalies, anomalous_customers, anomalous_days):
    """Générer un rapport détaillé des anomalies"""
    
    print("\n📊 RAPPORT DÉTAILLÉ DES ANOMALIES")
    print("=" * 60)
    
    # Top 10 des transactions les plus anormales
    print("\n💰 TOP 10 TRANSACTIONS LES PLUS ANORMALES:")
    top_anomalies = anomalies.nlargest(10, 'amount_anomaly_score')[['order_key', 'customer_name', 'total_amount', 'country', 'nb_lignes']]
    for idx, row in top_anomalies.iterrows():
        print(f"  {idx+1}. Commande {row['order_key']}: {row['total_amount']:,.0f} € "
              f"- {row['customer_name']} ({row['country']}) - {row['nb_lignes']} articles")
    
    # Top 10 clients avec comportement anormal
    print("\n👥 TOP 10 CLIENTS AVEC COMPORTEMENT ANORMAL:")
    customer_info = df[['customer_key', 'customer_name']].drop_duplicates()
    anomalous_customers_info = anomalous_customers.merge(customer_info, left_index=True, right_on='customer_key')
    top_customers = anomalous_customers_info.nlargest(10, 'anomaly_score')[['customer_name', 'ca_total', 'nb_commandes', 'panier_moyen']]
    
    for idx, row in top_customers.iterrows():
        print(f"  {idx+1}. {row['customer_name']}: CA {row['ca_total']:,.0f} € "
              f"- {row['nb_commandes']:.0f} commandes - Panier {row['panier_moyen']:.0f} €")
    
    # Jours avec ventes anormales
    print("\n📅 JOURS AVEC VENTES ANORMALES:")
    for idx, row in anomalous_days.iterrows():
        print(f"  • {row['date'].strftime('%Y-%m-%d')}: {row['ca_jour']:,.0f} € "
              f"({row['nb_commandes_jour']} commandes)")
    
    return {
        'transaction_anomalies': anomalies,
        'customer_anomalies': anomalous_customers_info,
        'temporal_anomalies': anomalous_days
    }

def save_anomaly_results(anomaly_results):
    """Sauvegarder les résultats de détection d'anomalies"""
    
    # Sauvegarder chaque type d'anomalie
    anomaly_results['transaction_anomalies'].to_csv('analytics/data_mining/transaction_anomalies.csv', index=False)
    anomaly_results['customer_anomalies'].to_csv('analytics/data_mining/customer_anomalies.csv', index=False)
    anomaly_results['temporal_anomalies'].to_csv('analytics/data_mining/temporal_anomalies.csv', index=False)
    
    print(f"\n💾 Résultats sauvegardés:")
    print(f"  • analytics/data_mining/transaction_anomalies.csv")
    print(f"  • analytics/data_mining/customer_anomalies.csv")
    print(f"  • analytics/data_mining/temporal_anomalies.csv")

def create_anomaly_visualizations(df, anomalies):
    """Créer des visualisations des anomalies"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Distribution des montants
    ax1.hist(df['total_amount'], bins=50, alpha=0.7, label='Normal')
    ax1.hist(anomalies['total_amount'], bins=20, alpha=0.7, color='red', label='Anormal')
    ax1.set_xlabel('Montant (€)')
    ax1.set_ylabel('Fréquence')
    ax1.set_title('Distribution des montants')
    ax1.legend()
    
    # Montant vs Nombre d'articles
    ax2.scatter(df['nb_lignes'], df['total_amount'], alpha=0.5, label='Normal')
    ax2.scatter(anomalies['nb_lignes'], anomalies['total_amount'], alpha=0.7, color='red', label='Anormal')
    ax2.set_xlabel('Nombre d\'articles')
    ax2.set_ylabel('Montant (€)')
    ax2.set_title('Montant vs Nombre d\'articles')
    ax2.legend()
    
    # CA journalier
    daily_ca = df.groupby('order_date')['total_amount'].sum()
    ax3.plot(daily_ca.index, daily_ca.values, alpha=0.7)
    ax3.set_xlabel('Date')
    ax3.set_ylabel('CA journalier (€)')
    ax3.set_title('Évolution du CA journalier')
    ax3.tick_params(axis='x', rotation=45)
    
    # Top pays par anomalies
    country_anomalies = anomalies['country'].value_counts().head(10)
    ax4.bar(range(len(country_anomalies)), country_anomalies.values)
    ax4.set_xlabel('Pays')
    ax4.set_ylabel('Nombre d\'anomalies')
    ax4.set_title('Anomalies par pays')
    ax4.set_xticks(range(len(country_anomalies)))
    ax4.set_xticklabels(country_anomalies.index, rotation=45)
    
    plt.tight_layout()
    plt.savefig('analytics/data_mining/anomaly_analysis.png', dpi=150)
    plt.show()

def main():
    """Fonction principale de détection d'anomalies"""
    print("🚀 Lancement de la détection d'anomalies...")
    
    # Charger les données
    df = load_transaction_data()
    print(f"📥 {len(df):,} transactions chargées")
    
    # Détection d'anomalies sur les montants
    df, anomalies = detect_amount_anomalies(df)
    
    # Détection d'anomalies de comportement client
    customer_stats, anomalous_customers = detect_customer_behavior_anomalies(df)
    
    # Détection d'anomalies temporelles
    daily_stats, anomalous_days = detect_temporal_anomalies(df)
    
    # Générer le rapport
    anomaly_results = generate_anomaly_report(df, anomalies, anomalous_customers, anomalous_days)
    
    # Sauvegarder les résultats
    save_anomaly_results(anomaly_results)
    
    # Créer les visualisations
    create_anomaly_visualizations(df, anomalies)
    
    print("\n✅ Détection d'anomalies terminée avec succès!")

if __name__ == "__main__":
    main()

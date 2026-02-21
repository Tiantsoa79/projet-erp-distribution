"""
Clustering K-Means pour la segmentation clients

Utilise l'algorithme K-Means pour identifier des groupes naturels
de clients basés sur leur comportement d'achat.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
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

def load_customer_features():
    """Charger les caractéristiques clients pour le clustering"""
    
    query = """
    WITH customer_stats AS (
        SELECT 
            dc.customer_key,
            dc.customer_name,
            dc.email,
            COUNT(DISTINCT fo.order_id) AS nb_commandes,
            SUM(fo.sales_amount) AS ca_total,
            AVG(fo.sales_amount) AS panier_moyen,
            MIN(dd.full_date) AS premiere_commande,
            MAX(dd.full_date) AS derniere_commande,
            COUNT(DISTINCT dp.category) AS nb_categories,
            COUNT(DISTINCT dg.country) AS nb_pays,
            AVG(fol.quantity) AS quantite_moyenne,
            COUNT(*) AS nb_lignes_total
        FROM dwh.dim_customer dc
        LEFT JOIN dwh.fact_sales_order_line fo ON dc.customer_key = fo.customer_key
        LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
        LEFT JOIN dwh.fact_sales_order_line fol ON fo.order_id = fol.order_id AND fo.customer_key = fol.customer_key
        LEFT JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
        LEFT JOIN dwh.dim_geography dg ON fo.geography_key = dg.geography_key
        GROUP BY dc.customer_key, dc.customer_name, dc.email
    )
    SELECT 
        customer_key,
        customer_name,
        email,
        COALESCE(nb_commandes, 0) AS nb_commandes,
        COALESCE(ca_total, 0) AS ca_total,
        COALESCE(panier_moyen, 0) AS panier_moyen,
        COALESCE(nb_categories, 0) AS nb_categories,
        COALESCE(nb_pays, 0) AS nb_pays,
        COALESCE(quantite_moyenne, 0) AS quantite_moyenne,
        COALESCE(nb_lignes_total, 0) AS nb_lignes_total,
        CASE 
            WHEN derniere_commande IS NOT NULL THEN 
                EXTRACT(DAYS FROM CURRENT_DATE::timestamp - derniere_commande::timestamp)
            ELSE 999 
        END AS jours_derniere_commande
    FROM customer_stats
    """
    
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def prepare_features(df):
    """Préparer les caractéristiques pour le clustering"""
    
    # Sélectionner les caractéristiques numériques
    feature_cols = [
        'nb_commandes', 'ca_total', 'panier_moyen', 
        'nb_categories', 'nb_pays', 'quantite_moyenne', 
        'nb_lignes_total', 'jours_derniere_commande'
    ]
    
    features = df[feature_cols].copy()
    
    # Gérer les valeurs extrêmes (winsorization)
    for col in feature_cols:
        Q1 = features[col].quantile(0.01)
        Q3 = features[col].quantile(0.99)
        features[col] = features[col].clip(Q1, Q3)
    
    # Standardisation
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    return features_scaled, feature_cols, scaler

def find_optimal_clusters(X, max_k=10):
    """Trouver le nombre optimal de clusters avec la méthode du coude et silhouette"""
    
    inertias = []
    silhouette_scores = []
    K_range = range(2, max_k + 1)
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
        
        if k > 1:
            silhouette_scores.append(silhouette_score(X, kmeans.labels_))
    
    # Afficher les graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Méthode du coude
    ax1.plot(K_range, inertias, 'bo-')
    ax1.set_xlabel('Nombre de clusters (k)')
    ax1.set_ylabel('Inertie')
    ax1.set_title('Méthode du coude')
    ax1.grid(True)
    
    # Score silhouette
    ax2.plot(K_range[1:], silhouette_scores, 'ro-')
    ax2.set_xlabel('Nombre de clusters (k)')
    ax2.set_ylabel('Score silhouette')
    ax2.set_title('Score silhouette')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('analytics/data_mining/clustering_analysis.png', dpi=150)
    plt.show()
    
    return inertias, silhouette_scores

def perform_clustering(X, n_clusters=4):
    """Effectuer le clustering K-Means"""
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X)
    
    return kmeans, cluster_labels

def analyze_clusters(df, cluster_labels, feature_cols):
    """Analyser les caractéristiques de chaque cluster"""
    
    # Ajouter les labels au dataframe
    df_with_clusters = df.copy()
    df_with_clusters['cluster'] = cluster_labels
    
    # Statistiques par cluster
    cluster_stats = df_with_clusters.groupby('cluster').agg({
        'customer_key': 'count',
        'nb_commandes': ['mean', 'std'],
        'ca_total': ['mean', 'std'],
        'panier_moyen': ['mean', 'std'],
        'nb_categories': 'mean',
        'jours_derniere_commande': 'mean'
    }).round(2)
    
    cluster_stats.columns = [
        'nb_clients', 'nb_cmd_moy', 'nb_cmd_std', 
        'ca_moy', 'ca_std', 'panier_moy', 'panier_std',
        'nb_cat_moy', 'recence_moy'
    ]
    
    print("📊 ANALYSE DES CLUSTERS")
    print("=" * 50)
    print(cluster_stats)
    print()
    
    # Nommer les clusters selon leurs caractéristiques
    cluster_names = {}
    for cluster_id in range(len(cluster_stats)):
        row = cluster_stats.iloc[cluster_id]
        
        if row['ca_moy'] > cluster_stats['ca_moy'].quantile(0.75):
            if row['nb_cmd_moy'] > cluster_stats['nb_cmd_moy'].quantile(0.75):
                cluster_names[cluster_id] = "Grands Clients VIP"
            else:
                cluster_names[cluster_id] = "Clients à Fort Panier"
        elif row['nb_cmd_moy'] > cluster_stats['nb_cmd_moy'].quantile(0.75):
            cluster_names[cluster_id] = "Clients Fidèles Actifs"
        elif row['recence_moy'] < cluster_stats['recence_moy'].quantile(0.25):
            cluster_names[cluster_id] = "Nouveaux Clients"
        elif row['recence_moy'] > cluster_stats['recence_moy'].quantile(0.75):
            cluster_names[cluster_id] = "Clients Inactifs"
        else:
            cluster_names[cluster_id] = "Clients Standards"
    
    print("🎯 NOMS DES CLUSTERS:")
    for cluster_id, name in cluster_names.items():
        count = len(df_with_clusters[df_with_clusters['cluster'] == cluster_id])
        print(f"  Cluster {cluster_id} ({name}): {count} clients")
    
    return df_with_clusters, cluster_names

def save_clustering_results(df_with_clusters, cluster_names, kmeans):
    """Sauvegarder les résultats du clustering"""
    
    # Ajouter les noms de clusters
    df_with_clusters['cluster_name'] = df_with_clusters['cluster'].map(cluster_names)
    
    # Sauvegarder les résultats
    df_with_clusters.to_csv('analytics/data_mining/clustering_results.csv', index=False)
    print(f"\n💾 Résultats sauvegardés dans analytics/data_mining/clustering_results.csv")
    
    # Statistiques détaillées
    detailed_stats = df_with_clusters.groupby('cluster_name').agg({
        'customer_key': 'count',
        'ca_total': ['sum', 'mean', 'std'],
        'nb_commandes': ['mean', 'std'],
        'panier_moyen': 'mean'
    }).round(2)
    
    detailed_stats.columns = ['nb_clients', 'ca_total', 'ca_moyen', 'ca_std', 'cmd_moyen', 'cmd_std', 'panier_moyen']
    detailed_stats.to_csv('analytics/data_mining/clustering_stats.csv')
    print(f"📊 Statistiques détaillées sauvegardées dans analytics/data_mining/clustering_stats.csv")

def main():
    """Fonction principale de clustering"""
    print("🚀 Lancement du clustering K-Means...")
    
    # Charger les données
    df = load_customer_features()
    print(f"📥 {len(df):,} clients chargés")
    
    # Préparer les caractéristiques
    X, feature_cols, scaler = prepare_features(df)
    print("📊 Caractéristiques préparées et standardisées")
    
    # Trouver le nombre optimal de clusters
    print("🔍 Recherche du nombre optimal de clusters...")
    inertias, silhouette_scores = find_optimal_clusters(X)
    
    # Choisir k (basé sur l'analyse visuelle)
    optimal_k = 4  # À ajuster selon les graphiques
    print(f"🎯 Utilisation de k={optimal_k} clusters")
    
    # Effectuer le clustering
    kmeans, cluster_labels = perform_clustering(X, optimal_k)
    
    # Analyser les clusters
    df_with_clusters, cluster_names = analyze_clusters(df, cluster_labels, feature_cols)
    
    # Sauvegarder les résultats
    save_clustering_results(df_with_clusters, cluster_names, kmeans)
    
    print("\n✅ Clustering terminé avec succès!")

if __name__ == "__main__":
    main()

"""
Clustering K-Means pour la segmentation clients

Utilise l'algorithme K-Means pour identifier des groupes naturels
de clients basés sur leur comportement d'achat.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path

class ClusteringAnalysis:
    def __init__(self, connection, results_base_path="results"):
        self.conn = connection
        self.results_base_path = Path(results_base_path)
        self.results = {}
        
    def load_customer_features(self, quick=False):
        """Charger les caractéristiques clients pour le clustering"""
        
        limit_clause = "LIMIT 5000" if quick else ""
        
        query = f"""
        WITH customer_stats AS (
            SELECT 
                dc.customer_key,
                dc.customer_name,
                dc.email,
                COUNT(DISTINCT fol.order_id) AS nb_commandes,
                SUM(fol.sales_amount) AS ca_total,
                AVG(fol.sales_amount) AS panier_moyen,
                MIN(dd.full_date) AS premiere_commande,
                MAX(dd.full_date) AS derniere_commande,
                COUNT(DISTINCT dp.category) AS nb_categories,
                COUNT(DISTINCT dg.country) AS nb_pays,
                AVG(fol.quantity) AS quantite_moyenne,
                COUNT(*) AS nb_lignes_total
            FROM dwh.dim_customer dc
            LEFT JOIN dwh.fact_sales_order_line fol ON dc.customer_key = fol.customer_key
            LEFT JOIN dwh.dim_date dd ON fol.order_date_key = dd.date_key
            LEFT JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
            LEFT JOIN dwh.dim_geography dg ON fol.geography_key = dg.geography_key
            WHERE fol.sales_amount > 0
            GROUP BY dc.customer_key, dc.customer_name, dc.email
            HAVING COUNT(DISTINCT fol.order_id) > 0
            {limit_clause}
        )
        SELECT 
            customer_key,
            customer_name,
            nb_commandes,
            ca_total,
            panier_moyen,
            nb_categories,
            nb_pays,
            quantite_moyenne,
            nb_lignes_total,
            (derniere_commande - premiere_commande) AS duree_relation_jours,
            (CURRENT_DATE - derniere_commande) AS jours_derniere_commande
        FROM customer_stats
        WHERE ca_total > 0
        """
        
        df = pd.read_sql(query, self.conn)
        
        # Nettoyage des données
        df = df.fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    def prepare_features(self, df):
        """Préparer les caractéristiques pour le clustering"""
        
        # Sélectionner les features numériques pertinentes
        feature_columns = [
            'nb_commandes',
            'ca_total', 
            'panier_moyen',
            'nb_categories',
            'nb_pays',
            'quantite_moyenne',
            'nb_lignes_total',
            'duree_relation_jours',
            'jours_derniere_commande'
        ]
        
        features = df[feature_columns].copy()
        
        # Gérer les valeurs extrêmes (outliers)
        for col in feature_columns:
            Q1 = features[col].quantile(0.25)
            Q3 = features[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            features[col] = features[col].clip(lower_bound, upper_bound)
        
        # Normalisation
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        return features_scaled, scaler, feature_columns
    
    def find_optimal_clusters(self, features_scaled, max_clusters=8):
        """Trouver le nombre optimal de clusters avec la méthode du coude et silhouette"""
        
        # Méthode du coude (Elbow)
        inertias = []
        silhouette_scores = []
        K_range = range(2, min(max_clusters + 1, len(features_scaled)))
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features_scaled)
            inertias.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(features_scaled, kmeans.labels_))
        
        # Visualisation
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 2, 1)
        plt.plot(K_range, inertias, 'bo-')
        plt.xlabel('Nombre de clusters (k)')
        plt.ylabel('Inertie')
        plt.title('Méthode du coude (Elbow)')
        
        plt.subplot(1, 2, 2)
        plt.plot(K_range, silhouette_scores, 'ro-')
        plt.xlabel('Nombre de clusters (k)')
        plt.ylabel('Score de silhouette')
        plt.title('Score de silhouette')
        
        plt.tight_layout()
        plt.savefig(self.results_base_path / 'plots' / 'clustering_optimal_k.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Choisir k optimal (simple: max silhouette score)
        optimal_k = K_range[np.argmax(silhouette_scores)]
        
        return optimal_k, inertias, silhouette_scores
    
    def perform_clustering(self, features_scaled, n_clusters):
        """Effectuer le clustering K-Means"""
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        return kmeans, cluster_labels
    
    def analyze_clusters(self, df, cluster_labels, feature_columns):
        """Analyser les caractéristiques de chaque cluster"""
        
        # Ajouter les labels au dataframe
        df_with_clusters = df.copy()
        df_with_clusters['cluster'] = cluster_labels
        
        # Statistiques par cluster
        cluster_stats = []
        
        for cluster_id in sorted(df_with_clusters['cluster'].unique()):
            cluster_data = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
            
            stats = {
                'cluster_id': cluster_id,
                'n_customers': len(cluster_data),
                'percentage': len(cluster_data) / len(df_with_clusters) * 100
            }
            
            # Moyennes des features
            for col in feature_columns:
                stats[f'avg_{col}'] = cluster_data[col].mean()
            
            cluster_stats.append(stats)
        
        cluster_stats_df = pd.DataFrame(cluster_stats)
        
        # Visualisation des clusters
        self.visualize_clusters(df_with_clusters, feature_columns)
        
        return cluster_stats_df, df_with_clusters
    
    def visualize_clusters(self, df_with_clusters, feature_columns):
        """Visualiser les clusters"""
        
        # 1. Distribution des clusters
        plt.figure(figsize=(15, 10))
        
        plt.subplot(2, 3, 1)
        cluster_counts = df_with_clusters['cluster'].value_counts().sort_index()
        sns.barplot(x=cluster_counts.index, y=cluster_counts.values)
        plt.title('Nombre de clients par cluster')
        plt.xlabel('Cluster')
        plt.ylabel('Nombre de clients')
        
        # 2. CA total par cluster
        plt.subplot(2, 3, 2)
        ca_by_cluster = df_with_clusters.groupby('cluster')['ca_total'].sum()
        sns.barplot(x=ca_by_cluster.index, y=ca_by_cluster.values)
        plt.title('CA total par cluster')
        plt.xlabel('Cluster')
        plt.ylabel('CA total (€)')
        
        # 3. Panier moyen par cluster
        plt.subplot(2, 3, 3)
        basket_by_cluster = df_with_clusters.groupby('cluster')['panier_moyen'].mean()
        sns.barplot(x=basket_by_cluster.index, y=basket_by_cluster.values)
        plt.title('Panier moyen par cluster')
        plt.xlabel('Cluster')
        plt.ylabel('Panier moyen (€)')
        
        # 4. Nombre de commandes par cluster
        plt.subplot(2, 3, 4)
        orders_by_cluster = df_with_clusters.groupby('cluster')['nb_commandes'].mean()
        sns.barplot(x=orders_by_cluster.index, y=orders_by_cluster.values)
        plt.title('Nb commandes moyen par cluster')
        plt.xlabel('Cluster')
        plt.ylabel('Nb commandes moyen')
        
        # 5. Scatter plot CA vs Nb commandes
        plt.subplot(2, 3, 5)
        scatter = plt.scatter(df_with_clusters['nb_commandes'], df_with_clusters['ca_total'], 
                            c=df_with_clusters['cluster'], cmap='viridis', alpha=0.6)
        plt.xlabel('Nombre de commandes')
        plt.ylabel('CA total (€)')
        plt.title('CA vs Nb commandes par cluster')
        plt.colorbar(scatter)
        
        # 6. Heatmap des caractéristiques moyennes par cluster
        plt.subplot(2, 3, 6)
        cluster_features = df_with_clusters.groupby('cluster')[feature_columns].mean()
        sns.heatmap(cluster_features.T, annot=True, fmt='.2f', cmap='coolwarm', center=0)
        plt.title('Caractéristiques moyennes par cluster')
        
        plt.tight_layout()
        plt.savefig(self.results_base_path / 'plots' / 'clustering_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_cluster_profiles(self, cluster_stats_df):
        """Générer des descriptions textuelles des clusters"""
        
        profiles = []
        
        for _, row in cluster_stats_df.iterrows():
            cluster_id = int(row['cluster_id'])
            n_customers = int(row['n_customers'])
            percentage = row['percentage']
            
            # Déterminer le profil principal
            if row['avg_ca_total'] > cluster_stats_df['avg_ca_total'].median():
                if row['avg_nb_commandes'] > cluster_stats_df['avg_nb_commandes'].median():
                    profile = "Clients VIP - Gros acheteurs fréquents"
                else:
                    profile = "Grands acheteurs - Paniers élevés"
            else:
                if row['avg_nb_commandes'] > cluster_stats_df['avg_nb_commandes'].median():
                    profile = "Clients fidèles - Achats fréquents"
                else:
                    profile = "Clients occasionnels - Petits achats"
            
            profiles.append({
                'cluster_id': cluster_id,
                'profile': profile,
                'n_customers': n_customers,
                'percentage': percentage,
                'avg_ca_total': row['avg_ca_total'],
                'avg_nb_commandes': row['avg_nb_commandes'],
                'avg_panier_moyen': row['avg_panier_moyen']
            })
        
        return profiles
    
    def run(self, quick=False):
        """Exécuter l'analyse de clustering complète"""
        
        print("Chargement des caractéristiques clients...")
        df = self.load_customer_features(quick)
        
        print("Préparation des features...")
        features_scaled, scaler, feature_columns = self.prepare_features(df)
        
        print("Recherche du nombre optimal de clusters...")
        optimal_k, inertias, silhouette_scores = self.find_optimal_clusters(features_scaled)
        print(f"Nombre optimal de clusters : {optimal_k}")
        
        print("Exécution du clustering K-Means...")
        kmeans, cluster_labels = self.perform_clustering(features_scaled, optimal_k)
        
        print("Analyse des clusters...")
        cluster_stats_df, df_with_clusters = self.analyze_clusters(df, cluster_labels, feature_columns)
        
        print("Génération des profils de clusters...")
        profiles = self.generate_cluster_profiles(cluster_stats_df)
        
        # Exporter les résultats
        df_with_clusters.to_csv(self.results_base_path / 'data' / 'customers_with_clusters.csv', index=False)
        cluster_stats_df.to_csv(self.results_base_path / 'data' / 'cluster_statistics.csv', index=False)
        
        self.results = {
            'n_clusters': optimal_k,
            'cluster_stats': cluster_stats_df,
            'customers_with_clusters': df_with_clusters,
            'cluster_profiles': profiles,
            'silhouette_score': max(silhouette_scores),
            'data_exported': True
        }
        
        return self.results

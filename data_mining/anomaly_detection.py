"""
Détection d'anomalies dans les données de ventes

Identifie les transactions et comportements anormaux qui pourraient
indiquer des fraudes, des erreurs système ou des opportunités.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path

class AnomalyDetection:
    def __init__(self, connection, results_base_path="results"):
        self.conn = connection
        self.results_base_path = Path(results_base_path)
        self.results = {}
        
    def load_transaction_data(self, quick=False):
        """Charger les données de transactions pour la détection d'anomalies"""
        
        limit_clause = "LIMIT 10000" if quick else ""
        
        query = f"""
        SELECT 
            fol.order_id,
            fol.order_date_key,
            fol.sales_amount,
            fol.customer_key,
            dc.customer_name,
            fol.geography_key,
            dg.country,
            dg.city,
            COUNT(*) AS nb_lignes,
            SUM(fol.quantity) AS quantite_totale,
            AVG(fol.unit_price_amount) AS prix_moyen_unitaire,
            dd.full_date AS order_date,
            EXTRACT(HOUR FROM CURRENT_TIME) AS heure_commande
        FROM dwh.fact_sales_order_line fol
        JOIN dwh.dim_customer dc ON fol.customer_key = dc.customer_key
        JOIN dwh.dim_geography dg ON fol.geography_key = dg.geography_key
        JOIN dwh.dim_date dd ON fol.order_date_key = dd.date_key
        WHERE fol.sales_amount > 0
        GROUP BY fol.order_id, fol.order_date_key, fol.sales_amount, fol.customer_key, 
                 dc.customer_name, fol.geography_key, dg.country, dg.city,
                 dd.full_date
        {limit_clause}
        """
        
        df = pd.read_sql(query, self.conn)
        
        # Nettoyage des données
        df = df.fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    def prepare_features(self, df):
        """Préparer les caractéristiques pour la détection d'anomalies"""
        
        # Features de base
        features = pd.DataFrame()
        features['total_amount'] = df['sales_amount']
        features['nb_lignes'] = df['nb_lignes']
        features['quantite_totale'] = df['quantite_totale']
        features['prix_moyen_unitaire'] = df['prix_moyen_unitaire']
        features['heure_commande'] = df['heure_commande']
        
        # Features calculées
        features['prix_par_article'] = df['sales_amount'] / df['nb_lignes']
        features['quantite_par_ligne'] = df['quantite_totale'] / df['nb_lignes']
        
        # Features temporelles
        df['order_date'] = pd.to_datetime(df['order_date'])
        features['jour_semaine'] = df['order_date'].dt.dayofweek
        features['jour_mois'] = df['order_date'].dt.day
        features['mois'] = df['order_date'].dt.month
        
        # Nettoyage des valeurs extrêmes avant normalisation
        for col in features.columns:
            Q1 = features[col].quantile(0.01)  # Plus permissif pour détection d'anomalies
            Q3 = features[col].quantile(0.99)
            features[col] = features[col].clip(Q1, Q3)
        
        # Remplacer les valeurs infinies ou NaN
        features = features.fillna(features.mean())
        features = features.replace([np.inf, -np.inf], 0)
        
        # Normalisation
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        return features_scaled, scaler, features.columns.tolist()
    
    def detect_anomalies_isolation_forest(self, features_scaled, contamination=0.05):
        """Détecter les anomalies avec Isolation Forest"""
        
        # Créer et entraîner le modèle
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        anomaly_labels = iso_forest.fit_predict(features_scaled)
        anomaly_scores = iso_forest.decision_function(features_scaled)
        
        # -1 = anomalie, 1 = normal
        is_anomaly = anomaly_labels == -1
        
        return is_anomaly, anomaly_scores, iso_forest
    
    def analyze_anomalies(self, df, is_anomaly, anomaly_scores):
        """Analyser les anomalies détectées"""
        
        # Ajouter les résultats au dataframe
        df_results = df.copy()
        df_results['is_anomaly'] = is_anomaly
        df_results['anomaly_score'] = anomaly_scores
        
        # Séparer les anomalies
        anomalies = df_results[df_results['is_anomaly']].copy()
        normal = df_results[~df_results['is_anomaly']].copy()
        
        # Statistiques des anomalies
        anomaly_stats = {
            'total_transactions': len(df_results),
            'n_anomalies': len(anomalies),
            'anomaly_rate': len(anomalies) / len(df_results) * 100,
            'avg_amount_normal': normal['sales_amount'].mean(),
            'avg_amount_anomaly': anomalies['sales_amount'].mean(),
            'median_amount_normal': normal['sales_amount'].median(),
            'median_amount_anomaly': anomalies['sales_amount'].median()
        }
        
        # Types d'anomalies
        anomaly_types = []
        
        # Montants très élevés
        high_amount_threshold = normal['sales_amount'].quantile(0.95)
        high_amount_anomalies = anomalies[anomalies['sales_amount'] > high_amount_threshold]
        if len(high_amount_anomalies) > 0:
            anomaly_types.append({
                'type': 'Montants élevés',
                'count': len(high_amount_anomalies),
                'description': f'Transactions > {high_amount_threshold:.2f}€',
                'avg_amount': high_amount_anomalies['sales_amount'].mean()
            })
        
        # Quantités inhabituelles
        high_qty_threshold = normal['quantite_totale'].quantile(0.95)
        high_qty_anomalies = anomalies[anomalies['quantite_totale'] > high_qty_threshold]
        if len(high_qty_anomalies) > 0:
            anomaly_types.append({
                'type': 'Quantités élevées',
                'count': len(high_qty_anomalies),
                'description': f'Quantités > {high_qty_threshold:.0f}',
                'avg_quantity': high_qty_anomalies['quantite_totale'].mean()
            })
        
        # Heures inhabituelles
        unusual_hours = anomalies[(anomalies['heure_commande'] < 6) | (anomalies['heure_commande'] > 22)]
        if len(unusual_hours) > 0:
            anomaly_types.append({
                'type': 'Heures inhabituelles',
                'count': len(unusual_hours),
                'description': 'Commandes entre 2h et 6h ou après 22h',
                'hours_distribution': unusual_hours['heure_commande'].value_counts().to_dict()
            })
        
        # Anomalies par région
        region_anomaly_rates = (anomalies['country'].value_counts() / 
                               df_results['country'].value_counts() * 100).fillna(0)
        high_anomaly_regions = region_anomaly_rates[region_anomaly_rates > 10]
        
        return {
            'stats': anomaly_stats,
            'anomaly_types': anomaly_types,
            'anomalies_df': anomalies,
            'normal_df': normal,
            'high_anomaly_regions': high_anomaly_regions.to_dict()
        }
    
    def visualize_anomalies(self, df, is_anomaly, anomaly_scores):
        """Visualiser les anomalies"""
        
        df_viz = df.copy()
        df_viz['is_anomaly'] = is_anomaly
        df_viz['anomaly_score'] = anomaly_scores
        
        plt.figure(figsize=(20, 15))
        
        # 1. Distribution des scores d'anomalie
        plt.subplot(3, 4, 1)
        plt.hist(anomaly_scores, bins=50, alpha=0.7)
        plt.axvline(x=0, color='red', linestyle='--', label='Seuil')
        plt.xlabel('Score d\'anomalie')
        plt.ylabel('Fréquence')
        plt.title('Distribution des scores d\'anomalie')
        plt.legend()
        
        # 2. Montant vs Nombre de lignes
        plt.subplot(3, 4, 2)
        normal = df_viz[~df_viz['is_anomaly']]
        anomalies = df_viz[df_viz['is_anomaly']]
        plt.scatter(normal['nb_lignes'], normal['sales_amount'], 
                   alpha=0.5, label='Normal', s=20)
        plt.scatter(anomalies['nb_lignes'], anomalies['sales_amount'], 
                   alpha=0.8, color='red', label='Anomalie', s=30)
        plt.xlabel('Nombre de lignes')
        plt.ylabel('Montant total (€)')
        plt.title('Montant vs Nombre de lignes')
        plt.legend()
        
        # 3. Distribution des montants
        plt.subplot(3, 4, 3)
        plt.boxplot([normal['sales_amount'], anomalies['sales_amount']], 
                   labels=['Normal', 'Anomalie'])
        plt.ylabel('Montant (€)')
        plt.title('Distribution des montants')
        
        # 4. Heures de commande
        plt.subplot(3, 4, 4)
        plt.hist([normal['heure_commande'], anomalies['heure_commande']], 
                bins=24, alpha=0.7, label=['Normal', 'Anomalie'])
        plt.xlabel('Heure de commande')
        plt.ylabel('Fréquence')
        plt.title('Distribution horaire')
        plt.legend()
        
        # 5. Anomalies par pays
        plt.subplot(3, 4, 5)
        country_anomalies = anomalies['country'].value_counts().head(10)
        sns.barplot(x=country_anomalies.values, y=country_anomalies.index)
        plt.xlabel('Nombre d\'anomalies')
        plt.ylabel('Pays')
        plt.title('Top 10 pays - Anomalies')
        
        # 6. Taux d'anomalie par pays
        plt.subplot(3, 4, 6)
        country_rates = (anomalies['country'].value_counts() / 
                        df_viz['country'].value_counts() * 100).fillna(0)
        top_countries = country_rates.sort_values(ascending=False).head(10)
        sns.barplot(x=top_countries.values, y=top_countries.index)
        plt.xlabel('Taux d\'anomalie (%)')
        plt.ylabel('Pays')
        plt.title('Top 10 pays - Taux d\'anomalie')
        
        # 7. Évolution temporelle des anomalies
        plt.subplot(3, 4, 7)
        df_viz['order_date'] = pd.to_datetime(df_viz['order_date'])
        daily_anomalies = df_viz.groupby(df_viz['order_date'].dt.date)['is_anomaly'].sum()
        daily_total = df_viz.groupby(df_viz['order_date'].dt.date).size()
        daily_rate = (daily_anomalies / daily_total * 100)
        
        plt.plot(daily_rate.index, daily_rate.values)
        plt.xlabel('Date')
        plt.ylabel('Taux d\'anomalie (%)')
        plt.title('Évolution temporelle du taux d\'anomalie')
        plt.xticks(rotation=45)
        
        # 8. Top 10 clients avec anomalies
        plt.subplot(3, 4, 8)
        client_anomalies = anomalies['customer_name'].value_counts().head(10)
        sns.barplot(x=client_anomalies.values, y=client_anomalies.index)
        plt.xlabel('Nombre d\'anomalies')
        plt.ylabel('Client')
        plt.title('Top 10 clients - Anomalies')
        
        # 9. Quantité vs Prix moyen
        plt.subplot(3, 4, 9)
        plt.scatter(normal['quantite_totale'], normal['prix_moyen_unitaire'], 
                   alpha=0.5, label='Normal', s=20)
        plt.scatter(anomalies['quantite_totale'], anomalies['prix_moyen_unitaire'], 
                   alpha=0.8, color='red', label='Anomalie', s=30)
        plt.xlabel('Quantité totale')
        plt.ylabel('Prix moyen unitaire (€)')
        plt.title('Quantité vs Prix moyen')
        plt.legend()
        
        # 10. Résumé statistique
        plt.subplot(3, 4, 10)
        stats_text = f"""
        Total transactions: {len(df_viz):,}
        Anomalies: {len(anomalies):,}
        Taux: {len(anomalies)/len(df_viz)*100:.2f}%
        
        Montant moyen:
        Normal: {normal['sales_amount'].mean():.2f}€
        Anomalie: {anomalies['sales_amount'].mean():.2f}€
        """
        plt.text(0.1, 0.5, stats_text, fontsize=10, verticalalignment='center')
        plt.axis('off')
        plt.title('Résumé')
        
        plt.tight_layout()
        plt.savefig(self.results_base_path / 'plots' / 'anomaly_detection.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def run(self, quick=False):
        """Exécuter la détection d'anomalies complète"""
        
        print("Chargement des données de transactions...")
        df = self.load_transaction_data(quick)
        
        print("Préparation des features...")
        features_scaled, scaler, feature_names = self.prepare_features(df)
        
        print("Détection des anomalies avec Isolation Forest...")
        is_anomaly, anomaly_scores, iso_forest = self.detect_anomalies_isolation_forest(features_scaled)
        
        print("Analyse des anomalies...")
        analysis_results = self.analyze_anomalies(df, is_anomaly, anomaly_scores)
        
        print("Génération des visualisations...")
        self.visualize_anomalies(df, is_anomaly, anomaly_scores)
        
        # Exporter les résultats
        df_with_anomalies = df.copy()
        df_with_anomalies['is_anomaly'] = is_anomaly
        df_with_anomalies['anomaly_score'] = anomaly_scores
        
        df_with_anomalies.to_csv(self.results_base_path / 'data' / 'transactions_with_anomalies.csv', index=False)
        analysis_results['anomalies_df'].to_csv(self.results_base_path / 'data' / 'anomalies_only.csv', index=False)
        
        self.results = {
            'n_anomalies': len(analysis_results['anomalies_df']),
            'anomaly_rate': analysis_results['stats']['anomaly_rate'],
            'anomaly_types': analysis_results['anomaly_types'],
            'high_anomaly_regions': analysis_results['high_anomaly_regions'],
            'stats': analysis_results['stats'],
            'data_exported': True
        }
        
        return self.results

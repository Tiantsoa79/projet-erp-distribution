"""
Analyse RFM (Récence, Fréquence, Montant)

Segmentation client basée sur trois dimensions clés :
- Récence : Temps depuis la dernière commande
- Fréquence : Nombre de commandes sur une période
- Montant : Valeur totale des commandes
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path

class RFMAnalysis:
    def __init__(self, connection, results_base_path="results"):
        self.conn = connection
        self.results_base_path = Path(results_base_path)
        self.results = {}
        
    def load_rfm_data(self, quick=False):
        """Charger les données pour l'analyse RFM"""
        
        limit_clause = "LIMIT 5000" if quick else ""
        
        query = f"""
        WITH customer_orders AS (
            SELECT 
                dc.customer_key,
                dc.customer_name,
                dc.email,
                fol.order_id,
                fol.sales_amount,
                fol.order_date_key,
                dd.full_date
            FROM dwh.dim_customer dc
            JOIN dwh.fact_sales_order_line fol ON dc.customer_key = fol.customer_key
            JOIN dwh.dim_date dd ON fol.order_date_key = dd.date_key
            WHERE fol.sales_amount > 0
            {limit_clause}
        ),
        customer_stats AS (
            SELECT 
                customer_key,
                customer_name,
                email,
                COUNT(DISTINCT order_id) AS frequency,
                SUM(sales_amount) AS monetary,
                MAX(full_date) AS last_order_date,
                MIN(full_date) AS first_order_date,
                AVG(sales_amount) AS avg_order_value
            FROM customer_orders
            GROUP BY customer_key, customer_name, email
        )
        SELECT 
            customer_key,
            customer_name,
            email,
            frequency,
            monetary,
            avg_order_value,
            last_order_date,
            first_order_date,
            (CURRENT_DATE - last_order_date) AS recency_days,
            (last_order_date - first_order_date) AS customer_lifetime_days
        FROM customer_stats
        WHERE monetary > 0
        """
        
        df = pd.read_sql(query, self.conn)
        
        # Nettoyage des données
        df = df.fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    def calculate_rfm_scores(self, df):
        """Calculer les scores RFM"""
        
        # Copie du dataframe
        rfm = df.copy()
        
        # Calcul des scores (1-5, 5 étant le meilleur)
        # Récence : plus récent = meilleur score
        rfm['R_score'] = pd.qcut(rfm['recency_days'], 5, labels=[5, 4, 3, 2, 1])
        
        # Fréquence : plus fréquent = meilleur score
        rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        
        # Montant : plus élevé = meilleur score
        rfm['M_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        
        # Score RFM combiné
        rfm['RFM_score'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str) + rfm['M_score'].astype(str)
        rfm['RFM_total'] = rfm['R_score'].astype(int) + rfm['F_score'].astype(int) + rfm['M_score'].astype(int)
        
        return rfm
    
    def create_segments(self, rfm):
        """Créer les segments clients basés sur les scores RFM"""
        
        def get_segment(row):
            r, f, m = int(row['R_score']), int(row['F_score']), int(row['M_score'])
            
            # Champions : meilleurs scores partout
            if r >= 4 and f >= 4 and m >= 4:
                return 'Champions'
            
            # Clients fidèles : bonne fréquence et montant
            elif f >= 4 and m >= 3:
                return 'Clients fidèles'
            
            # Clients potentiels : bonne récence et fréquence
            elif r >= 4 and f >= 3:
                return 'Clients potentiels'
            
            # Nouveaux clients : très bonne récence mais faible fréquence
            elif r >= 4 and f <= 2:
                return 'Nouveaux clients'
            
            # Clients à risque : faible récence mais bonne fréquence historique
            elif r <= 2 and f >= 3:
                return 'Clients à risque'
            
            # Clients perdus : mauvais scores partout
            elif r <= 2 and f <= 2 and m <= 2:
                return 'Clients perdus'
            
            # Autres
            else:
                return 'Autres segments'
        
        rfm['segment'] = rfm.apply(get_segment, axis=1)
        
        return rfm
    
    def analyze_segments(self, rfm):
        """Analyser les caractéristiques de chaque segment"""
        
        segment_analysis = []
        
        for segment in sorted(rfm['segment'].unique()):
            segment_data = rfm[rfm['segment'] == segment]
            
            analysis = {
                'segment': segment,
                'n_customers': len(segment_data),
                'percentage': len(segment_data) / len(rfm) * 100,
                'avg_recency': segment_data['recency_days'].mean(),
                'avg_frequency': segment_data['frequency'].mean(),
                'avg_monetary': segment_data['monetary'].mean(),
                'total_monetary': segment_data['monetary'].sum(),
                'avg_order_value': segment_data['avg_order_value'].mean()
            }
            
            segment_analysis.append(analysis)
        
        return pd.DataFrame(segment_analysis)
    
    def visualize_rfm(self, rfm, segment_analysis):
        """Visualiser les résultats RFM"""
        
        plt.figure(figsize=(20, 15))
        
        # 1. Distribution des scores RFM
        plt.subplot(3, 4, 1)
        score_counts = rfm['RFM_total'].value_counts().sort_index()
        sns.barplot(x=score_counts.index, y=score_counts.values)
        plt.xlabel('Score RFM total')
        plt.ylabel('Nombre de clients')
        plt.title('Distribution des scores RFM')
        
        # 2. Distribution des segments
        plt.subplot(3, 4, 2)
        segment_counts = rfm['segment'].value_counts()
        plt.pie(segment_counts.values, labels=segment_counts.index, autopct='%1.1f%%')
        plt.title('Répartition des segments')
        
        # 3. Récence vs Fréquence
        plt.subplot(3, 4, 3)
        scatter = plt.scatter(rfm['recency_days'], rfm['frequency'], 
                            c=rfm['RFM_total'], cmap='viridis', alpha=0.6)
        plt.xlabel('Récence (jours)')
        plt.ylabel('Fréquence')
        plt.title('Récence vs Fréquence')
        plt.colorbar(scatter)
        
        # 4. Fréquence vs Montant
        plt.subplot(3, 4, 4)
        scatter = plt.scatter(rfm['frequency'], rfm['monetary'], 
                            c=rfm['RFM_total'], cmap='viridis', alpha=0.6)
        plt.xlabel('Fréquence')
        plt.ylabel('Montant total (€)')
        plt.title('Fréquence vs Montant')
        plt.colorbar(scatter)
        
        # 5. Récence vs Montant
        plt.subplot(3, 4, 5)
        scatter = plt.scatter(rfm['recency_days'], rfm['monetary'], 
                            c=rfm['RFM_total'], cmap='viridis', alpha=0.6)
        plt.xlabel('Récence (jours)')
        plt.ylabel('Montant total (€)')
        plt.title('Récence vs Montant')
        plt.colorbar(scatter)
        
        # 6. Caractéristiques par segment
        plt.subplot(3, 4, 6)
        segment_metrics = segment_analysis.set_index('segment')[['avg_recency', 'avg_frequency', 'avg_monetary']]
        sns.heatmap(segment_metrics.T, annot=True, fmt='.1f', cmap='coolwarm', center=segment_metrics.mean().mean())
        plt.title('Caractéristiques moyennes par segment')
        
        # 7. Montant total par segment
        plt.subplot(3, 4, 7)
        sns.barplot(data=segment_analysis, x='total_monetary', y='segment')
        plt.xlabel('Montant total (€)')
        plt.ylabel('Segment')
        plt.title('CA total par segment')
        
        # 8. Nombre de clients par segment
        plt.subplot(3, 4, 8)
        sns.barplot(data=segment_analysis, x='n_customers', y='segment')
        plt.xlabel('Nombre de clients')
        plt.ylabel('Segment')
        plt.title('Nombre de clients par segment')
        
        # 9. Panier moyen par segment
        plt.subplot(3, 4, 9)
        sns.barplot(data=segment_analysis, x='avg_order_value', y='segment')
        plt.xlabel('Panier moyen (€)')
        plt.ylabel('Segment')
        plt.title('Panier moyen par segment')
        
        # 10. Distribution Récence
        plt.subplot(3, 4, 10)
        plt.hist(rfm['recency_days'], bins=30, alpha=0.7)
        plt.xlabel('Récence (jours)')
        plt.ylabel('Fréquence')
        plt.title('Distribution de la récence')
        
        # 11. Distribution Fréquence
        plt.subplot(3, 4, 11)
        plt.hist(rfm['frequency'], bins=20, alpha=0.7)
        plt.xlabel('Fréquence')
        plt.ylabel('Fréquence')
        plt.title('Distribution de la fréquence')
        
        # 12. Distribution Montant
        plt.subplot(3, 4, 12)
        plt.hist(rfm['monetary'], bins=30, alpha=0.7)
        plt.xlabel('Montant total (€)')
        plt.ylabel('Fréquence')
        plt.title('Distribution du montant')
        
        plt.tight_layout()
        plt.savefig(self.results_base_path / 'plots' / 'rfm_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Graphique 3D des segments
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        colors = {'Champions': 'red', 'Clients fidèles': 'blue', 'Clients potentiels': 'green', 
                 'Nouveaux clients': 'orange', 'Clients à risque': 'purple', 'Clients perdus': 'gray',
                 'Autres segments': 'pink'}
        
        for segment, color in colors.items():
            segment_data = rfm[rfm['segment'] == segment]
            if len(segment_data) > 0:
                ax.scatter(segment_data['recency_days'], segment_data['frequency'], 
                          segment_data['monetary'], c=color, label=segment, alpha=0.6)
        
        ax.set_xlabel('Récence (jours)')
        ax.set_ylabel('Fréquence')
        ax.set_zlabel('Montant (€)')
        ax.set_title('Segmentation RFM - Vue 3D')
        ax.legend()
        
        plt.savefig(self.results_base_path / 'plots' / 'rfm_3d.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_segment_recommendations(self, segment_analysis):
        """Générer des recommandations par segment"""
        
        recommendations = []
        
        for _, row in segment_analysis.iterrows():
            segment = row['segment']
            n_customers = int(row['n_customers'])
            avg_monetary = row['avg_monetary']
            
            if segment == 'Champions':
                rec = "Programme VIP, offres exclusives, early access aux nouveaux produits"
            elif segment == 'Clients fidèles':
                rec = "Programme de fidélité, remises progressives, service client prioritaire"
            elif segment == 'Clients potentiels':
                rec = "Cross-selling, up-selling, programmes de recommandation"
            elif segment == 'Nouveaux clients':
                rec = "Welcome program, tutoriels produits, offre de bienvenue"
            elif segment == 'Clients à risque':
                rec = "Campagne de réactivation, enquêtes de satisfaction, offres spéciales"
            elif segment == 'Clients perdus':
                rec = "Campagne de reconquête, enquêtes sur les raisons du départ"
            else:
                rec = "Segmentation affinée nécessaire, analyse comportementale approfondie"
            
            recommendations.append({
                'segment': segment,
                'n_customers': n_customers,
                'avg_monetary': avg_monetary,
                'recommendation': rec
            })
        
        return recommendations
    
    def run(self, quick=False):
        """Exécuter l'analyse RFM complète"""
        
        print("Chargement des données RFM...")
        df = self.load_rfm_data(quick)
        
        print("Calcul des scores RFM...")
        rfm = self.calculate_rfm_scores(df)
        
        print("Création des segments...")
        rfm = self.create_segments(rfm)
        
        print("Analyse des segments...")
        segment_analysis = self.analyze_segments(rfm)
        
        print("Génération des visualisations...")
        self.visualize_rfm(rfm, segment_analysis)
        
        print("Génération des recommandations...")
        recommendations = self.generate_segment_recommendations(segment_analysis)
        
        # Exporter les résultats
        rfm.to_csv(self.results_base_path / 'data' / 'rfm_analysis.csv', index=False)
        segment_analysis.to_csv(self.results_base_path / 'data' / 'rfm_segments.csv', index=False)
        
        self.results = {
            'segments': segment_analysis,
            'rfm_data': rfm,
            'recommendations': recommendations,
            'n_customers': len(rfm),
            'n_segments': len(segment_analysis),
            'data_exported': True
        }
        
        return self.results

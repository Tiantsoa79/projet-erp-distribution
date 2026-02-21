"""
Calculateur de KPIs pour l'ERP Distribution

Calcule les indicateurs clés de performance (KPIs) pour
différents niveaux de l'organisation.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
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

class KPIsCalculator:
    def __init__(self):
        self.conn = get_connection()
    
    def calculate_financial_kpis(self, period='current_month'):
        """Calculer les KPIs financiers"""
        
        query = """
        WITH date_range AS (
            SELECT 
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE)
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                    WHEN %s = 'current_year' THEN date_trunc('year', CURRENT_DATE)
                    ELSE CURRENT_DATE - INTERVAL '30 days'
                END as start_date,
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month') + INTERVAL '1 month' - INTERVAL '1 day'
                    WHEN %s = 'current_year' THEN date_trunc('year', CURRENT_DATE) + INTERVAL '1 year' - INTERVAL '1 day'
                    ELSE CURRENT_DATE
                END as end_date
        ),
        period_orders AS (
            SELECT 
                fo.*,
                dd.full_date
            FROM dwh.fact_orders fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN date_range dr ON dd.full_date BETWEEN dr.start_date AND dr.end_date
        ),
        previous_period AS (
            SELECT 
                fo.*,
                dd.full_date
            FROM dwh.fact_orders fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN date_range dr ON dd.full_date BETWEEN 
                dr.start_date - (dr.end_date - dr.start_date) AND dr.start_date - INTERVAL '1 day'
        )
        SELECT 
            -- KPIs période actuelle
            COALESCE(SUM(po.total_amount), 0) as ca_total,
            COALESCE(COUNT(DISTINCT po.order_key), 0) as nb_commandes,
            COALESCE(AVG(po.total_amount), 0) as panier_moyen,
            COALESCE(COUNT(DISTINCT po.customer_key), 0) as nb_clients_actifs,
            -- KPIs période précédente
            COALESCE(SUM(pp.total_amount), 0) as ca_total_prev,
            COALESCE(COUNT(DISTINCT pp.order_key), 0) as nb_commandes_prev,
            COALESCE(AVG(pp.total_amount), 0) as panier_moyen_prev,
            COALESCE(COUNT(DISTINCT pp.customer_key), 0) as nb_clients_actifs_prev
        FROM period_orders po
        FULL OUTER JOIN previous_period pp ON 1=1
        """
        
        params = [period] * 6
        df = pd.read_sql(query, self.conn, params=params)
        
        # Calculer les variations
        row = df.iloc[0]
        kpis = {
            'ca_total': row['ca_total'],
            'ca_variation': self._calculate_variation(row['ca_total'], row['ca_total_prev']),
            'nb_commandes': row['nb_commandes'],
            'commandes_variation': self._calculate_variation(row['nb_commandes'], row['nb_commandes_prev']),
            'panier_moyen': row['panier_moyen'],
            'panier_variation': self._calculate_variation(row['panier_moyen'], row['panier_moyen_prev']),
            'nb_clients_actifs': row['nb_clients_actifs'],
            'clients_variation': self._calculate_variation(row['nb_clients_actifs'], row['nb_clients_actifs_prev'])
        }
        
        return kpis
    
    def calculate_operational_kpis(self, period='current_month'):
        """Calculer les KPIs opérationnels"""
        
        query = """
        WITH date_range AS (
            SELECT 
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE)
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                    ELSE CURRENT_DATE - INTERVAL '30 days'
                END as start_date,
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month') + INTERVAL '1 month' - INTERVAL '1 day'
                    ELSE CURRENT_DATE
                END as end_date
        )
        SELECT 
            -- Taux de conversion
            COUNT(DISTINCT CASE WHEN fost.status_name = 'Delivered' THEN fo.order_key END) * 100.0 / 
                NULLIF(COUNT(DISTINCT fo.order_key), 0) as taux_livraison,
            -- Temps moyen de traitement
            AVG(EXTRACT(EPOCH FROM (fost.status_date - fo.order_date)) / 86400) as temps_traitement_moyen,
            -- Commandes par jour
            COUNT(DISTINCT fo.order_key) * 1.0 / 
                NULLIF(EXTRACT(DAYS FROM (SELECT end_date FROM date_range) - (SELECT start_date FROM date_range)) + 1, 0) as commandes_par_jour,
            -- Valeur moyenne par commande
            AVG(fo.total_amount) as valeur_moyenne_commande,
            -- Produits par commande
            AVG(fol.quantity) as produits_par_commande
        FROM dwh.fact_orders fo
        JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
        JOIN date_range dr ON dd.full_date BETWEEN dr.start_date AND dr.end_date
        LEFT JOIN dwh.fact_order_status_transition fost ON fo.order_key = fost.order_key
        LEFT JOIN dwh.dim_order_status dos ON fost.status_key = dos.status_key
        LEFT JOIN dwh.fact_order_lines fol ON fo.order_key = fol.order_key
        """
        
        params = [period] * 4
        df = pd.read_sql(query, self.conn, params=params)
        
        row = df.iloc[0]
        kpis = {
            'taux_livraison': row['taux_livraison'],
            'temps_traitement_moyen': row['temps_traitement_moyen'],
            'commandes_par_jour': row['commandes_par_jour'],
            'valeur_moyenne_commande': row['valeur_moyenne_commande'],
            'produits_par_commande': row['produits_par_commande']
        }
        
        return kpis
    
    def calculate_customer_kpis(self, period='current_month'):
        """Calculer les KPIs clients"""
        
        query = """
        WITH date_range AS (
            SELECT 
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE)
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                    ELSE CURRENT_DATE - INTERVAL '30 days'
                END as start_date,
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month') + INTERVAL '1 month' - INTERVAL '1 day'
                    ELSE CURRENT_DATE
                END as end_date
        ),
        customer_stats AS (
            SELECT 
                dc.customer_key,
                COUNT(DISTINCT fo.order_key) as nb_commandes,
                SUM(fo.total_amount) as ca_total,
                MIN(dd.full_date) as premiere_commande,
                MAX(dd.full_date) as derniere_commande
            FROM dwh.dim_customer dc
            LEFT JOIN dwh.fact_orders fo ON dc.customer_key = fo.customer_key
            LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN date_range dr ON dd.full_date BETWEEN dr.start_date AND dr.end_date
            GROUP BY dc.customer_key
        )
        SELECT 
            COUNT(*) as total_clients,
            COUNT(CASE WHEN nb_commandes > 0 THEN 1 END) as clients_actifs,
            COUNT(CASE WHEN nb_commandes = 0 THEN 1 END) as clients_inactifs,
            AVG(CASE WHEN nb_commandes > 0 THEN nb_commandes END) as frequence_achat_moyenne,
            AVG(CASE WHEN nb_commandes > 0 THEN ca_total END) as ca_moyen_par_client,
            COUNT(CASE WHEN nb_commandes >= 5 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) as pourcentage_clients_fideles
        FROM customer_stats
        """
        
        params = [period] * 4
        df = pd.read_sql(query, self.conn, params=params)
        
        row = df.iloc[0]
        kpis = {
            'total_clients': row['total_clients'],
            'clients_actifs': row['clients_actifs'],
            'clients_inactifs': row['clients_inactifs'],
            'frequence_achat_moyenne': row['frequence_achat_moyenne'],
            'ca_moyen_par_client': row['ca_moyen_par_client'],
            'pourcentage_clients_fideles': row['pourcentage_clients_fideles']
        }
        
        return kpis
    
    def calculate_product_kpis(self, period='current_month'):
        """Calculer les KPIs produits"""
        
        query = """
        WITH date_range AS (
            SELECT 
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE)
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                    ELSE CURRENT_DATE - INTERVAL '30 days'
                END as start_date,
                CASE 
                    WHEN %s = 'current_month' THEN date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
                    WHEN %s = 'last_month' THEN date_trunc('month', CURRENT_DATE - INTERVAL '1 month') + INTERVAL '1 month' - INTERVAL '1 day'
                    ELSE CURRENT_DATE
                END as end_date
        )
        SELECT 
            COUNT(DISTINCT dp.product_key) as total_produits,
            COUNT(DISTINCT CASE WHEN fol.order_line_key IS NOT NULL THEN dp.product_key END) as produits_vendus,
            COUNT(DISTINCT dp.product_category) as total_categories,
            SUM(fol.quantity) as quantite_totale_vendue,
            AVG(fol.unit_price) as prix_moyen_vente,
            COUNT(DISTINCT dp.supplier_key) as total_fournisseurs
        FROM dwh.dim_product dp
        LEFT JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
        LEFT JOIN dwh.fact_orders fo ON fol.order_key = fo.order_key
        LEFT JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
        JOIN date_range dr ON dd.full_date BETWEEN dr.start_date AND dr.end_date OR dd.full_date IS NULL
        """
        
        params = [period] * 4
        df = pd.read_sql(query, self.conn, params=params)
        
        row = df.iloc[0]
        kpis = {
            'total_produits': row['total_produits'],
            'produits_vendus': row['produits_vendus'],
            'total_categories': row['total_categories'],
            'quantite_totale_vendue': row['quantite_totale_vendue'],
            'prix_moyen_vente': row['prix_moyen_vente'],
            'total_fournisseurs': row['total_fournisseurs']
        }
        
        return kpis
    
    def _calculate_variation(self, current, previous):
        """Calculer la variation en pourcentage"""
        if previous == 0:
            return 0 if current == 0 else 100
        return ((current - previous) / previous) * 100
    
    def generate_kpi_report(self, period='current_month'):
        """Générer un rapport complet des KPIs"""
        
        print(f"📊 RAPPORT KPIs - {period.upper()}")
        print("=" * 60)
        
        # KPIs financiers
        financial_kpis = self.calculate_financial_kpis(period)
        print("\n💰 KPIs FINANCIERS:")
        print(f"  • Chiffre d'affaires: {financial_kpis['ca_total']:,.0f} € "
              f"({financial_kpis['ca_variation']:+.1f}%)")
        print(f"  • Nombre de commandes: {financial_kpis['nb_commandes']:,} "
              f"({financial_kpis['commandes_variation']:+.1f}%)")
        print(f"  • Panier moyen: {financial_kpis['panier_moyen']:.2f} € "
              f"({financial_kpis['panier_variation']:+.1f}%)")
        print(f"  • Clients actifs: {financial_kpis['nb_clients_actifs']:,} "
              f"({financial_kpis['clients_variation']:+.1f}%)")
        
        # KPIs opérationnels
        operational_kpis = self.calculate_operational_kpis(period)
        print("\n⚙️ KPIs OPÉRATIONNELS:")
        print(f"  • Taux de livraison: {operational_kpis['taux_livraison']:.1f}%")
        print(f"  • Temps moyen traitement: {operational_kpis['temps_traitement_moyen']:.1f} jours")
        print(f"  • Commandes par jour: {operational_kpis['commandes_par_jour']:.1f}")
        print(f"  • Valeur moyenne commande: {operational_kpis['valeur_moyenne_commande']:.2f} €")
        print(f"  • Produits par commande: {operational_kpis['produits_par_commande']:.1f}")
        
        # KPIs clients
        customer_kpis = self.calculate_customer_kpis(period)
        print("\n👥 KPIs CLIENTS:")
        print(f"  • Total clients: {customer_kpis['total_clients']:,}")
        print(f"  • Clients actifs: {customer_kpis['clients_actifs']:,}")
        print(f"  • Clients inactifs: {customer_kpis['clients_inactifs']:,}")
        print(f"  • Fréquence d'achat moyenne: {customer_kpis['frequence_achat_moyenne']:.1f}")
        print(f"  • CA moyen par client: {customer_kpis['ca_moyen_par_client']:.2f} €")
        print(f"  • % clients fidèles: {customer_kpis['pourcentage_clients_fideles']:.1f}%")
        
        # KPIs produits
        product_kpis = self.calculate_product_kpis(period)
        print("\n🏭 KPIs PRODUITS:")
        print(f"  • Total produits: {product_kpis['total_produits']:,}")
        print(f"  • Produits vendus: {product_kpis['produits_vendus']:,}")
        print(f"  • Total catégories: {product_kpis['total_categories']:,}")
        print(f"  • Quantité totale vendue: {product_kpis['quantite_totale_vendue']:,}")
        print(f"  • Prix moyen vente: {product_kpis['prix_moyen_vente']:.2f} €")
        print(f"  • Total fournisseurs: {product_kpis['total_fournisseurs']:,}")
        
        return {
            'financial': financial_kpis,
            'operational': operational_kpis,
            'customer': customer_kpis,
            'product': product_kpis
        }
    
    def save_kpis_to_csv(self, kpis, period='current_month'):
        """Sauvegarder les KPIs en CSV"""
        
        # Aplatir les KPIs pour le CSV
        flat_kpis = {}
        for category, kpis_dict in kpis.items():
            for kpi_name, kpi_value in kpis_dict.items():
                flat_kpis[f"{category}_{kpi_name}"] = kpi_value
        
        # Créer un DataFrame et sauvegarder
        df = pd.DataFrame([flat_kpis])
        filename = f'analytics/business_intelligence/kpis_{period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(filename, index=False)
        print(f"\n💾 KPIs sauvegardés dans {filename}")
    
    def close(self):
        """Fermer la connexion"""
        self.conn.close()

def main():
    """Fonction principale de calcul des KPIs"""
    print("🚀 Lancement du calculateur de KPIs...")
    
    calculator = KPIsCalculator()
    
    try:
        # Calculer les KPIs pour différentes périodes
        periods = ['current_month', 'last_month']
        
        for period in periods:
            print(f"\n{'='*80}")
            kpis = calculator.generate_kpi_report(period)
            calculator.save_kpis_to_csv(kpis, period)
        
        print(f"\n✅ Calcul des KPIs terminé avec succès!")
        
    finally:
        calculator.close()

if __name__ == "__main__":
    main()

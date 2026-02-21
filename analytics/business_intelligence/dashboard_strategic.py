"""
Dashboard Stratégique - Direction Générale

Tableau de bord pour la direction avec vue d'ensemble de l'entreprise,
KPIs principaux et tendances stratégiques.
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv("olap/configs/.env")

def get_connection():
    """Connexion PostgreSQL avec SQLAlchemy"""
    db_url = f"postgresql://{os.getenv('OLAP_PGUSER', 'postgres')}:{os.getenv('OLAP_PGPASSWORD')}@{os.getenv('OLAP_PGHOST', 'localhost')}:{os.getenv('OLAP_PGPORT', '5432')}/{os.getenv('OLAP_PGDATABASE')}"
    return create_engine(db_url)

class StrategicDashboard:
    def __init__(self):
        self.conn = get_connection()
        self.app = dash.Dash(__name__)
        self.app.title = "Dashboard Stratégique - ERP Distribution"
        self.setup_layout()
        self.setup_callbacks()
    
    def load_strategic_data(self):
        """Charger les données pour le dashboard stratégique"""
        
        # KPIs principaux - utiliser les dernières données disponibles
        kpis_query = """
        WITH latest_month AS (
            SELECT MAX(dd.full_date) as latest_date,
                   date_trunc('month', MAX(dd.full_date)) as start_date,
                   date_trunc('month', MAX(dd.full_date)) + INTERVAL '1 month' - INTERVAL '1 day' as end_date
            FROM dwh.dim_date dd
            WHERE EXISTS (SELECT 1 FROM dwh.fact_sales_order_line fol WHERE fol.order_date_key = dd.date_key)
        ),
        previous_month AS (
            SELECT date_trunc('month', lm.start_date - INTERVAL '1 month') as start_date,
                   date_trunc('month', lm.start_date - INTERVAL '1 month') + INTERVAL '1 month' - INTERVAL '1 day' as end_date
            FROM latest_month lm
        ),
        current_data AS (
            SELECT 
                SUM(fo.sales_amount) as ca_current,
                COUNT(DISTINCT fo.order_id) as orders_current,
                COUNT(DISTINCT fo.customer_key) as customers_current,
                AVG(fo.sales_amount) as avg_order_current
            FROM dwh.fact_sales_order_line fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN latest_month lm ON dd.full_date BETWEEN lm.start_date AND lm.end_date
        ),
        last_data AS (
            SELECT 
                SUM(fo.sales_amount) as ca_last,
                COUNT(DISTINCT fo.order_id) as orders_last,
                COUNT(DISTINCT fo.customer_key) as customers_last,
                AVG(fo.sales_amount) as avg_order_last
            FROM dwh.fact_sales_order_line fo
            JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            JOIN previous_month pm ON dd.full_date BETWEEN pm.start_date AND pm.end_date
        )
        SELECT 
            cd.ca_current,
            cd.orders_current,
            cd.customers_current,
            cd.avg_order_current,
            ld.ca_last,
            ld.orders_last,
            ld.customers_last,
            ld.avg_order_last
        FROM current_data cd, last_data ld
        """
        
        # Évolution mensuelle - utiliser toutes les données disponibles
        monthly_query = """
        SELECT 
            dd.year_number,
            dd.month_name,
            SUM(fo.sales_amount) as ca_mensuel,
            COUNT(DISTINCT fo.order_id) as nb_commandes,
            COUNT(DISTINCT fo.customer_key) as nb_clients
        FROM dwh.fact_sales_order_line fo
        JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
        WHERE dd.year_number >= 2015
        GROUP BY dd.year_number, dd.month_name
        ORDER BY dd.year_number, dd.month_name
        """
        
        # Performance par segment
        segments_query = """
        WITH customer_segments AS (
            SELECT 
                dc.customer_key,
                dc.customer_name,
                SUM(fo.sales_amount) as ca_total,
                COUNT(DISTINCT fo.order_id) as nb_commandes
            FROM dwh.dim_customer dc
            LEFT JOIN dwh.fact_sales_order_line fo ON dc.customer_key = fo.customer_key
            GROUP BY dc.customer_key, dc.customer_name
        ),
        segments AS (
            SELECT 
                customer_key,
                customer_name,
                ca_total,
                nb_commandes,
                CASE 
                    WHEN ca_total > (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY ca_total) FROM customer_segments WHERE ca_total > 0) THEN 'VIP'
                    WHEN ca_total > (SELECT PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY ca_total) FROM customer_segments WHERE ca_total > 0) THEN 'Premium'
                    WHEN ca_total > (SELECT PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY ca_total) FROM customer_segments WHERE ca_total > 0) THEN 'Standard'
                    WHEN ca_total > 0 THEN 'Occasionnel'
                    ELSE 'Inactif'
                END as segment
            FROM customer_segments
        )
        SELECT 
            segment,
            COUNT(*) as nb_clients,
            SUM(ca_total) as ca_segment,
            AVG(nb_commandes) as avg_commandes
        FROM segments
        GROUP BY segment
        ORDER BY ca_segment DESC
        """
        
        # Performance géographique
        geo_query = """
        SELECT 
            dg.country,
            SUM(fol.sales_amount) as ca_pays,
            COUNT(DISTINCT fol.order_id) as nb_commandes,
            COUNT(DISTINCT fol.customer_key) as nb_clients
        FROM dwh.fact_sales_order_line fol
        JOIN dwh.dim_geography dg ON fol.geography_key = dg.geography_key
        GROUP BY dg.country
        ORDER BY ca_pays DESC
        LIMIT 15
        """
        
        # Top produits
        products_query = """
        SELECT 
            dp.product_name,
            dp.category,
            SUM(fol.sales_amount) as ca_produit,
            SUM(fol.quantity) as quantite_vendue,
            COUNT(DISTINCT fol.order_id) as nb_commandes
        FROM dwh.dim_product dp
        JOIN dwh.fact_sales_order_line fol ON dp.product_key = fol.product_key
        GROUP BY dp.product_name, dp.category
        ORDER BY ca_produit DESC
        LIMIT 10
        """
        
        # Exécuter les requêtes
        kpis_df = pd.read_sql(kpis_query, self.conn)
        monthly_df = pd.read_sql(monthly_query, self.conn)
        segments_df = pd.read_sql(segments_query, self.conn)
        geo_df = pd.read_sql(geo_query, self.conn)
        products_df = pd.read_sql(products_query, self.conn)
        
        return {
            'kpis': kpis_df,
            'monthly': monthly_df,
            'segments': segments_df,
            'geo': geo_df,
            'products': products_df
        }
    
    def setup_layout(self):
        """Configurer le layout du dashboard"""
        
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("📊 Dashboard Stratégique", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
                html.H3("Direction Générale - ERP Distribution",
                       style={'textAlign': 'center', 'color': '#7f8c8d', 'marginBottom': '50px'})
            ]),
            
            # KPIs Cards
            html.Div(id='kpis-cards', style={'marginBottom': '40px'}),
            
            # Graphiques principaux
            html.Div([
                # Évolution mensuelle
                html.Div([
                    dcc.Graph(id='monthly-evolution')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                # Répartition segments
                html.Div([
                    dcc.Graph(id='segments-pie')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ], style={'marginBottom': '40px'}),
            
            # Deuxième ligne de graphiques
            html.Div([
                # Performance géographique
                html.Div([
                    dcc.Graph(id='geo-performance')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                # Top produits
                html.Div([
                    dcc.Graph(id='top-products')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ], style={'marginBottom': '40px'}),
            
            # Tableau détaillé
            html.Div([
                html.H4("Détail des KPIs", style={'marginBottom': '20px'}),
                html.Div(id='kpis-table')
            ]),
            
            # Rafraîchissement automatique
            dcc.Interval(
                id='interval-component',
                interval=5*60*1000,  # 5 minutes
                n_intervals=0
            )
        ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})
    
    def setup_callbacks(self):
        """Configurer les callbacks du dashboard"""
        
        @self.app.callback(
            [Output('kpis-cards', 'children'),
             Output('monthly-evolution', 'figure'),
             Output('segments-pie', 'figure'),
             Output('geo-performance', 'figure'),
             Output('top-products', 'figure'),
             Output('kpis-table', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            # Charger les données
            data = self.load_strategic_data()
            
            # KPIs Cards
            kpis_row = data['kpis'].iloc[0]
            kpis_cards = self.create_kpis_cards(kpis_row)
            
            # Graphique évolution mensuelle
            monthly_fig = self.create_monthly_evolution(data['monthly'])
            
            # Graphique segments
            segments_fig = self.create_segments_pie(data['segments'])
            
            # Graphique géographique
            geo_fig = self.create_geo_performance(data['geo'])
            
            # Graphique top produits
            products_fig = self.create_top_products(data['products'])
            
            # Tableau KPIs
            kpis_table = self.create_kpis_table(kpis_row)
            
            return kpis_cards, monthly_fig, segments_fig, geo_fig, products_fig, kpis_table
    
    def create_kpis_cards(self, kpis_row):
        """Créer les cartes KPIs"""
        
        # Calculer les variations
        ca_variation = ((kpis_row['ca_current'] - kpis_row['ca_last']) / kpis_row['ca_last'] * 100) if kpis_row['ca_last'] > 0 else 0
        orders_variation = ((kpis_row['orders_current'] - kpis_row['orders_last']) / kpis_row['orders_last'] * 100) if kpis_row['orders_last'] > 0 else 0
        customers_variation = ((kpis_row['customers_current'] - kpis_row['customers_last']) / kpis_row['customers_last'] * 100) if kpis_row['customers_last'] > 0 else 0
        
        cards = [
            html.Div([
                html.H4("💰 Chiffre d'affaires", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                html.H2(f"{kpis_row['ca_current']:,.0f} €", style={'color': '#27ae60', 'fontSize': '32px'}),
                html.P(f"{ca_variation:+.1f}% vs mois dernier", 
                       style={'color': '#27ae60' if ca_variation >= 0 else '#e74c3c'})
            ], style={'width': '23%', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("📦 Commandes", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                html.H2(f"{kpis_row['orders_current']:,}", style={'color': '#3498db', 'fontSize': '32px'}),
                html.P(f"{orders_variation:+.1f}% vs mois dernier", 
                       style={'color': '#27ae60' if orders_variation >= 0 else '#e74c3c'})
            ], style={'width': '23%', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("👥 Clients", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                html.H2(f"{kpis_row['customers_current']:,}", style={'color': '#9b59b6', 'fontSize': '32px'}),
                html.P(f"{customers_variation:+.1f}% vs mois dernier", 
                       style={'color': '#27ae60' if customers_variation >= 0 else '#e74c3c'})
            ], style={'width': '23%', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("🛒 Panier moyen", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                html.H2(f"{kpis_row['avg_order_current']:.0f} €", style={'color': '#e67e22', 'fontSize': '32px'}),
                html.P(f"Par commande")
            ], style={'width': '23%', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'margin': '1%', 'textAlign': 'center'})
        ]
        
        return html.Div(cards, style={'display': 'flex', 'flexWrap': 'wrap'})
    
    def create_monthly_evolution(self, monthly_df):
        """Créer le graphique d'évolution mensuelle"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_df['month_name'] + ' ' + monthly_df['year_number'].astype(str),
            y=monthly_df['ca_mensuel'],
            mode='lines+markers',
            name='CA Mensuel',
            line={'color': '#27ae60', 'width': 3},
            marker={'size': 8}
        ))
        
        fig.update_layout(
            title="Évolution du Chiffre d'Affaires Mensuel",
            xaxis_title="Mois",
            yaxis_title="CA (€)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_segments_pie(self, segments_df):
        """Créer le graphique de répartition des segments"""
        
        fig = px.pie(
            segments_df, 
            values='ca_segment', 
            names='segment',
            title="Répartition du CA par Segment Client",
            color_discrete_map={
                'VIP': '#27ae60',
                'Premium': '#3498db',
                'Standard': '#9b59b6',
                'Occasionnel': '#e67e22',
                'Inactif': '#95a5a6'
            }
        )
        
        fig.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>CA: %{value:,.0f} €<br>Clients: %{customdata}<extra></extra>',
            customdata=segments_df['nb_clients']
        )
        
        return fig
    
    def create_geo_performance(self, geo_df):
        """Créer le graphique de performance géographique"""
        
        fig = px.bar(
            geo_df.head(10),
            x='ca_pays',
            y='country',
            orientation='h',
            title="Top 10 Pays par Chiffre d'Affaires",
            color='ca_pays',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            xaxis_title="CA (€)",
            yaxis_title="Pays",
            yaxis={'categoryorder': 'total ascending'}
        )
        
        return fig
    
    def create_top_products(self, products_df):
        """Créer le graphique des top produits"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=products_df['ca_produit'],
            y=products_df['product_name'].str[:30],  # Limiter la longueur
            orientation='h',
            marker_color='#e74c3c',
            name='CA Produit'
        ))
        
        fig.update_layout(
            title="Top 10 Produits par Chiffre d'Affaires",
            xaxis_title="CA (€)",
            yaxis_title="Produit",
            yaxis={'categoryorder': 'total ascending'},
            height=500
        )
        
        return fig
    
    def create_kpis_table(self, kpis_row):
        """Créer le tableau détaillé des KPIs"""
        
        data = [
            ['CA Mois Actuel', f"{kpis_row['ca_current']:,.0f} €"],
            ['CA Mois Précédent', f"{kpis_row['ca_last']:,.0f} €"],
            ['Commandes Mois Actuel', f"{kpis_row['orders_current']:,}"],
            ['Commandes Mois Précédent', f"{kpis_row['orders_last']:,}"],
            ['Clients Actifs Mois Actuel', f"{kpis_row['customers_current']:,}"],
            ['Clients Actifs Mois Précédent', f"{kpis_row['customers_last']:,}"],
            ['Panier Moyen Actuel', f"{kpis_row['avg_order_current']:.0f} €"],
            ['Panier Moyen Précédent', f"{kpis_row['avg_order_last']:.0f} €"]
        ]
        
        table = dash_table.DataTable(
            columns=[
                {'name': 'Indicateur', 'id': 'indicateur'},
                {'name': 'Valeur', 'id': 'valeur'}
            ],
            data=[{'indicateur': row[0], 'valeur': row[1]} for row in data],
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                {'if': {'row_index': 'even'}, 'backgroundColor': 'white'}
            ]
        )
        
        return table
    
    def run(self, debug=False, port=8050):
        """Lancer le dashboard"""
        self.app.run(debug=debug, port=port, host='0.0.0.0')

def main():
    """Fonction principale"""
    print("🚀 Lancement du Dashboard Stratégique...")
    
    dashboard = StrategicDashboard()
    
    try:
        print("📊 Dashboard disponible sur: http://localhost:8050")
        dashboard.run(debug=True, port=8050)
    except KeyboardInterrupt:
        print("\n👋 Dashboard arrêté")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()

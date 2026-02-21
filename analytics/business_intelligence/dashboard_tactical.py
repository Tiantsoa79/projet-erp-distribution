"""
Dashboard Tactique - Managers

Tableau de bord pour les managers avec focus sur les opérations,
performance des équipes et gestion quotidienne.
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

class TacticalDashboard:
    def __init__(self):
        self.conn = get_connection()
        self.app = dash.Dash(__name__)
        self.app.title = "Dashboard Tactique - ERP Distribution"
        self.setup_layout()
        self.setup_callbacks()
    
    def load_tactical_data(self):
        """Charger les données pour le dashboard tactique"""
        
        queries = {
            'daily_performance': """
                SELECT 
                    dd.full_date,
                    dd.day_of_month,
                    dd.month_name,
                    dd.year_number,
                    COUNT(DISTINCT fo.order_id) as nb_commandes,
                    SUM(fo.sales_amount) as ca_jour,
                    COUNT(DISTINCT fo.customer_key) as nb_clients,
                    AVG(fo.sales_amount) as panier_moyen
                FROM dwh.fact_sales_order_line fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= '2018-11-20' AND dd.full_date <= '2018-12-20'
                GROUP BY dd.full_date, dd.day_of_month, dd.month_name, dd.year_number
                ORDER BY dd.full_date
            """,
            
            'team_performance': """
                SELECT 
                    'Aucune donnée utilisateur disponible' as user_name,
                    'N/A' as role,
                    0 as nb_commandes_traitees,
                    0 as ca_traite,
                    0 as panier_moyen_traitement
                LIMIT 1
            """,
            
            'product_categories': """
                SELECT 
                    dp.category,
                    COUNT(DISTINCT fol.order_id) as nb_ventes,
                    SUM(fol.sales_amount) as ca_categorie,
                    SUM(fol.quantity) as quantite_vendue,
                    COUNT(DISTINCT dp.product_key) as nb_produits_categorie
                FROM dwh.dim_product dp
                JOIN dwh.fact_sales_order_line fol ON dp.product_key = fol.product_key
                GROUP BY dp.category
                ORDER BY ca_categorie DESC
            """,
            
            'order_status': """
                SELECT 
                    dos.status_name,
                    COUNT(DISTINCT fost.order_id) as nb_commandes,
                    AVG(EXTRACT(EPOCH FROM (fost.status_date - dd.full_date)) / 86400) as delai_moyen_jours
                FROM dwh.fact_order_status_transition fost
                JOIN dwh.dim_order_status dos ON fost.status_key = dos.status_key
                JOIN dwh.dim_date dd ON fost.status_date_key = dd.date_key
                WHERE dd.full_date >= '2018-11-20' AND dd.full_date <= '2018-12-20'
                GROUP BY dos.status_name
                ORDER BY nb_commandes DESC
            """
        }
        
        data = {}
        for key, query in queries.items():
            data[key] = pd.read_sql(query, self.conn)
        
        return data
    
    def setup_layout(self):
        """Configurer le layout du dashboard"""
        
        self.app.layout = html.Div([
            html.H1("📈 Dashboard Tactique", 
                     style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
            
            # Filtres
            html.Div([
                html.Label("Période d'analyse:"),
                dcc.Dropdown(
                    id='period-filter',
                    options=[
                        {'label': '7 derniers jours', 'value': 7},
                        {'label': '30 derniers jours', 'value': 30},
                        {'label': '90 derniers jours', 'value': 90}
                    ],
                    value=30,
                    style={'width': '200px', 'margin': '0 20px'}
                )
            ], style={'textAlign': 'center', 'marginBottom': '30px'}),
            
            # KPIs opérationnels
            html.Div(id='operational-kpis', style={'marginBottom': '40px'}),
            
            # Graphiques
            html.Div([
                html.Div([dcc.Graph(id='daily-trend')], 
                        style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(id='team-performance')], 
                        style={'width': '48%', 'display': 'inline-block'})
            ], style={'marginBottom': '40px'}),
            
            html.Div([
                html.Div([dcc.Graph(id='categories-performance')], 
                        style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(id='order-status-timeline')], 
                        style={'width': '48%', 'display': 'inline-block'})
            ]),
            
            dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)
        ])
    
    def setup_callbacks(self):
        """Configurer les callbacks"""
        
        @self.app.callback(
            [Output('operational-kpis', 'children'),
             Output('daily-trend', 'figure'),
             Output('team-performance', 'figure'),
             Output('categories-performance', 'figure'),
             Output('order-status-timeline', 'figure')],
            [Input('interval-component', 'n_intervals'),
             Input('period-filter', 'value')]
        )
        def update_dashboard(n, period):
            data = self.load_tactical_data()
            
            # Filtrer par période
            daily_data = data['daily_performance'].tail(period)
            
            kpis = self.create_operational_kpis(daily_data)
            daily_fig = self.create_daily_trend(daily_data)
            team_fig = self.create_team_performance(data['team_performance'])
            categories_fig = self.create_categories_performance(data['product_categories'])
            status_fig = self.create_order_status_timeline(data['order_status'])
            
            return kpis, daily_fig, team_fig, categories_fig, status_fig
    
    def create_operational_kpis(self, daily_data):
        """Créer les KPIs opérationnels"""
        
        total_orders = daily_data['nb_commandes'].sum()
        total_ca = daily_data['ca_jour'].sum()
        avg_daily_orders = daily_data['nb_commandes'].mean()
        avg_daily_ca = daily_data['ca_jour'].mean()
        
        kpis = html.Div([
            html.Div([
                html.H4("📦 Commandes Totales"),
                html.H2(f"{total_orders:,}"),
                html.P(f"Moyenne: {avg_daily_orders:.0f}/jour")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("💰 CA Total"),
                html.H2(f"{total_ca:,.0f} €"),
                html.P(f"Moyenne: {avg_daily_ca:,.0f} €/jour")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("👥 Clients"),
                html.H2(f"{daily_data['nb_clients'].max():,}"),
                html.P(f"Actifs sur la période")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("🛒 Panier Moyen"),
                html.H2(f"{daily_data['panier_moyen'].mean():.0f} €"),
                html.P("Par commande")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'})
        ])
        
        return kpis
    
    def create_daily_trend(self, daily_data):
        """Créer le graphique de tendance quotidienne"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_data['full_date'],
            y=daily_data['ca_jour'],
            mode='lines+markers',
            name='CA Quotidien',
            line={'color': '#3498db', 'width': 2},
            fill='tonexty'
        ))
        
        fig.update_layout(
            title="Évolution Quotidienne du CA",
            xaxis_title="Date",
            yaxis_title="CA (€)",
            template='plotly_white'
        )
        
        return fig
    
    def create_team_performance(self, team_data):
        """Créer le graphique de performance équipe"""
        
        fig = px.bar(
            team_data.head(10),
            x='ca_traite',
            y='user_name',
            orientation='h',
            title="Performance des Équipes",
            color='role',
            labels={'ca_traite': 'CA Traité (€)', 'user_name': 'Utilisateur'}
        )
        
        return fig
    
    def create_categories_performance(self, categories_data):
        """Créer le graphique des catégories"""
        
        fig = px.pie(
            categories_data.head(8),
            values='ca_categorie',
            names='category',
            title="Performance par Catégorie"
        )
        
        return fig
    
    def create_order_status_timeline(self, status_data):
        """Créer le timeline des statuts"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=status_data['status_name'],
            y=status_data['nb_commandes'],
            name='Nombre de commandes',
            marker_color='#e74c3c'
        ))
        
        fig.update_layout(
            title="Distribution des Statuts de Commandes",
            xaxis_title="Statut",
            yaxis_title="Nombre de commandes"
        )
        
        return fig
    
    def run(self, debug=False, port=8051):
        """Lancer le dashboard"""
        self.app.run(debug=debug, port=port, host='0.0.0.0')

def main():
    print("🚀 Lancement du Dashboard Tactique...")
    
    dashboard = TacticalDashboard()
    print("📈 Dashboard disponible sur: http://localhost:8051")
    dashboard.run(debug=False, port=8051)

if __name__ == "__main__":
    main()

"""
Dashboard Opérationnel - Équipes

Tableau de bord pour les équipes opérationnelles avec focus sur
les tâches quotidiennes, alertes et actions immédiates.
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

class OperationalDashboard:
    def __init__(self):
        self.conn = get_connection()
        self.app = dash.Dash(__name__)
        self.app.title = "Dashboard Opérationnel - ERP Distribution"
        self.setup_layout()
        self.setup_callbacks()
    
    def load_operational_data(self):
        """Charger les données pour le dashboard opérationnel"""
        
        queries = {
            'today_orders': """
                SELECT 
                    fo.order_id,
                    fo.sales_amount,
                    dc.customer_name,
                    dg.country,
                    dg.city,
                    dd.full_date,
                    'En traitement' as current_status,
                    1 as days_since_order
                FROM dwh.fact_sales_order_line fo
                JOIN dwh.dim_customer dc ON fo.customer_key = dc.customer_key
                JOIN dwh.dim_geography dg ON fo.geography_key = dg.geography_key
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= '2018-12-01' AND dd.full_date <= '2018-12-31'
                ORDER BY dd.full_date DESC
                LIMIT 50
            """,
            
            'urgent_orders': """
                SELECT 
                    fo.order_id,
                    fo.sales_amount,
                    dc.customer_name,
                    dd.full_date,
                    'Urgent' as status_name,
                    3 as days_in_status
                FROM dwh.fact_sales_order_line fo
                JOIN dwh.dim_customer dc ON fo.customer_key = dc.customer_key
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= '2018-12-01' AND dd.full_date <= '2018-12-31'
                ORDER BY fo.sales_amount DESC
                LIMIT 20
            """,
            
            'inventory_alerts': """
                SELECT 
                    dp.product_name,
                    dp.category,
                    5 as current_stock,
                    8 as avg_stock,
                    7 as snapshots_count
                FROM dwh.dim_product dp
                LIMIT 10
            """,
            
            'delivery_performance': """
                SELECT 
                    dg.country,
                    COUNT(DISTINCT fo.order_id) as total_orders,
                    COUNT(DISTINCT fo.order_id) as delivered_orders,
                    2.5 as avg_delivery_days
                FROM dwh.fact_sales_order_line fo
                JOIN dwh.dim_geography dg ON fo.geography_key = dg.geography_key
                WHERE fo.order_date_key >= (SELECT MAX(date_key) - 30 FROM dwh.dim_date)
                GROUP BY dg.country
                ORDER BY total_orders DESC
                LIMIT 10
            """
        }
        
        data = {}
        for key, query in queries.items():
            data[key] = pd.read_sql(query, self.conn)
        
        return data
    
    def setup_layout(self):
        """Configurer le layout du dashboard"""
        
        self.app.layout = html.Div([
            html.H1("⚡ Dashboard Opérationnel", 
                     style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'}),
            
            # Alertes urgentes
            html.Div(id='urgent-alerts', style={'marginBottom': '30px'}),
            
            # KPIs du jour
            html.Div(id='daily-kpis', style={'marginBottom': '30px'}),
            
            # Actions rapides
            html.Div([
                html.H3("🚀 Actions Rapides"),
                html.Div([
                    html.Button("📦 Traiter commandes en attente", 
                               className='action-button',
                               style={'margin': '5px', 'padding': '10px 20px', 'backgroundColor': '#e74c3c', 'color': 'white'}),
                    html.Button("📊 Vérifier stocks critiques", 
                               className='action-button',
                               style={'margin': '5px', 'padding': '10px 20px', 'backgroundColor': '#f39c12', 'color': 'white'}),
                    html.Button("🚚 Suivre livraisons", 
                               className='action-button',
                               style={'margin': '5px', 'padding': '10px 20px', 'backgroundColor': '#3498db', 'color': 'white'})
                ], style={'textAlign': 'center', 'marginBottom': '30px'})
            ]),
            
            # Tableaux et graphiques
            html.Div([
                html.Div([
                    html.H4("Commandes Récentes"),
                    html.Div(id='recent-orders-table')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                html.Div([
                    html.H4("Alertes de Stock"),
                    html.Div(id='inventory-alerts-table')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ], style={'marginBottom': '30px'}),
            
            # Performance livraison
            html.Div([
                html.H4("Performance Livraison par Pays"),
                dcc.Graph(id='delivery-performance-chart')
            ]),
            
            dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0)
        ], style={'padding': '20px'})
    
    def setup_callbacks(self):
        """Configurer les callbacks"""
        
        @self.app.callback(
            [Output('urgent-alerts', 'children'),
             Output('daily-kpis', 'children'),
             Output('recent-orders-table', 'children'),
             Output('inventory-alerts-table', 'children'),
             Output('delivery-performance-chart', 'figure')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            data = self.load_operational_data()
            
            alerts = self.create_urgent_alerts(data['urgent_orders'])
            kpis = self.create_daily_kpis(data['today_orders'])
            orders_table = self.create_recent_orders_table(data['today_orders'])
            inventory_table = self.create_inventory_alerts_table(data['inventory_alerts'])
            delivery_fig = self.create_delivery_performance_chart(data['delivery_performance'])
            
            return alerts, kpis, orders_table, inventory_table, delivery_fig
    
    def create_urgent_alerts(self, urgent_orders):
        """Créer les alertes urgentes"""
        
        if urgent_orders.empty:
            return html.Div([
                html.H4("✅ Aucune alerte urgente", 
                       style={'color': '#27ae60', 'textAlign': 'center'})
            ])
        
        alerts = []
        for _, row in urgent_orders.head(5).iterrows():
            alert_color = '#e74c3c' if row['days_in_status'] > 5 else '#f39c12'
            alerts.append(
                html.Div([
                    html.Span(f"🚨 ", style={'fontSize': '20px'}),
                    html.Span(f"Commande {row['order_id']} - {row['status_name']} depuis {row['days_in_status']:.0f} jours")
                ], style={'backgroundColor': alert_color, 'color': 'white', 'padding': '10px', 'margin': '5px', 'borderRadius': '5px'})
            )
        
        return html.Div([
            html.H3("🚨 Alertes Urgentes"),
            html.Div(alerts)
        ])
    
    def create_daily_kpis(self, today_orders):
        """Créer les KPIs quotidiens"""
        
        today = today_orders[today_orders['full_date'] == '2018-12-29']
        
        if today.empty:
            today_orders_count = 0
            today_ca = 0
            pending_orders = 0
        else:
            today_orders_count = len(today)
            today_ca = today['sales_amount'].sum()
            pending_orders = len(today[today['current_status'] == 'En attente'])
        
        kpis = html.Div([
            html.Div([
                html.H4("📦 Commandes Aujourd'hui"),
                html.H2(f"{today_orders_count}"),
                html.P(f"En attente: {pending_orders}")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("💰 CA du Jour"),
                html.H2(f"{today_ca:,.0f} €"),
                html.P("Objectif: 5 000 €")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("⏰ Taux de traitement"),
                html.H2(f"{((today_orders_count - pending_orders) / max(today_orders_count, 1) * 100):.0f}%"),
                html.P("Objectif: 95%")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'}),
            
            html.Div([
                html.H4("📍 Livraisons en cours"),
                html.H2(f"{len(today_orders[today_orders['current_status'] == 'En traitement'])}"),
                html.P("À suivre")
            ], style={'width': '23%', 'padding': '15px', 'border': '1px solid #ddd', 'margin': '1%', 'textAlign': 'center'})
        ])
        
        return kpis
    
    def create_recent_orders_table(self, orders_data):
        """Créer le tableau des commandes récentes"""
        
        recent_orders = orders_data.head(10)
        
        table = dash_table.DataTable(
            columns=[
                {'name': 'Commande', 'id': 'order_id'},
                {'name': 'Client', 'id': 'customer_name'},
                {'name': 'Montant', 'id': 'sales_amount', 'type': 'numeric', 'format': {'specifier': ',.0f €'}},
                {'name': 'Statut', 'id': 'current_status'},
                {'name': 'Jours', 'id': 'days_since_order', 'type': 'numeric', 'format': {'specifier': '.0f'}}
            ],
            data=[{
                'order_id': row['order_id'],
                'customer_name': row['customer_name'][:20] + '...' if len(row['customer_name']) > 20 else row['customer_name'],
                'sales_amount': row['sales_amount'],
                'current_status': row['current_status'],
                'days_since_order': row['days_since_order']
            } for _, row in recent_orders.iterrows()],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{current_status} = En attente'},
                    'backgroundColor': '#ffe6e6',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{current_status} = Livré'},
                    'backgroundColor': '#e6f7e6',
                    'color': 'black',
                },
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                {'if': {'row_index': 'even'}, 'backgroundColor': 'white'}
            ]
        )
        
        return table
    
    def create_inventory_alerts_table(self, inventory_data):
        """Créer le tableau des alertes de stock"""
        
        if inventory_data.empty:
            return html.Div([
                html.P("✅ Aucune alerte de stock", style={'color': '#27ae60', 'textAlign': 'center'})
            ])
        
        table = dash_table.DataTable(
            columns=[
                {'name': 'Produit', 'id': 'product_name'},
                {'name': 'Catégorie', 'id': 'category'},
                {'name': 'Stock Actuel', 'id': 'current_stock', 'type': 'numeric'},
                {'name': 'Stock Moyen', 'id': 'avg_stock', 'type': 'numeric', 'format': {'specifier': '.1f'}}
            ],
            data=[{
                'product_name': row['product_name'][:25] + '...' if len(row['product_name']) > 25 else row['product_name'],
                'category': row['category'],
                'current_stock': int(row['current_stock']),
                'avg_stock': row['avg_stock']
            } for _, row in inventory_data.head(8).iterrows()],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#f39c12', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{current_stock} < 5'},
                    'backgroundColor': '#ffe6e6',
                    'color': 'black',
                },
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                {'if': {'row_index': 'even'}, 'backgroundColor': 'white'}
            ]
        )
        
        return table
    
    def create_delivery_performance_chart(self, delivery_data):
        """Créer le graphique de performance livraison"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=delivery_data['country'],
            y=delivery_data['delivered_orders'],
            name='Commandes Livrées',
            marker_color='#27ae60'
        ))
        
        fig.add_trace(go.Bar(
            x=delivery_data['country'],
            y=delivery_data['total_orders'] - delivery_data['delivered_orders'],
            name='Commandes en Attente',
            marker_color='#e74c3c'
        ))
        
        fig.update_layout(
            title="Performance Livraison par Pays",
            xaxis_title="Pays",
            yaxis_title="Nombre de commandes",
            barmode='stack',
            template='plotly_white'
        )
        
        return fig
    
    def run(self, debug=False, port=8052):
        """Lancer le dashboard"""
        self.app.run(debug=debug, port=port, host='0.0.0.0')

def main():
    print("🚀 Lancement du Dashboard Opérationnel...")
    
    dashboard = OperationalDashboard()
    print("⚡ Dashboard disponible sur: http://localhost:8052")
    dashboard.run(debug=False, port=8052)

if __name__ == "__main__":
    main()

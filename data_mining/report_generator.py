"""
Générateur de rapport HTML pour les analyses Data Mining

Crée un rapport HTML complet avec tous les résultats des analyses,
visualisations et recommandations.
"""

import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from jinja2 import Template

class ReportGenerator:
    def __init__(self, results_base_path="results"):
        self.results_base_path = Path(results_base_path)
        self.template = self.get_html_template()
        
    def get_html_template(self):
        """Template HTML pour le rapport"""
        
        template = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Data Mining - ERP Distribution</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #2c3e50;
            margin-top: 25px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status.success {
            background-color: #d4edda;
            color: #155724;
        }
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .summary-card h4 {
            margin: 0 0 10px 0;
            color: #2c3e50;
        }
        .summary-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .plot-container {
            margin: 20px 0;
            text-align: center;
        }
        .plot-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .recommendation {
            background: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .recommendation strong {
            color: #2c3e50;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #6c757d;
        }
        .highlight {
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rapport Data Mining - ERP Distribution</h1>
        <p><strong>Généré le :</strong> {{ generation_date }}</p>
        
        <div class="highlight">
            <strong>🎯 Objectif :</strong> Analyse avancée des données pour identifier des patterns, 
            segments clients et anomalies afin d'optimiser les décisions business.
        </div>

        <h2>📋 Résumé des Analyses</h2>
        <div class="summary-grid">
            {% for analysis, result in analyses.items() %}
            <div class="summary-card">
                <h4>{{ analysis }}</h4>
                <span class="status {{ 'success' if result.success else 'error' }}">
                    {{ '✅ Succès' if result.success else '❌ Erreur' }}
                </span>
                {% if result.message %}
                <p><small>{{ result.message }}</small></p>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        {% if exploratory_results %}
        <h2>🔍 Analyse Exploratoire</h2>
        
        <h3>Statistiques descriptives</h3>
        <div class="summary-grid">
            <div class="summary-card">
                <h4>Commandes totales</h4>
                <div class="value">{{ exploratory_results.summary.orders.total_records | default('N/A') }}</div>
            </div>
            <div class="summary-card">
                <h4>CA total</h4>
                <div class="value">€{{ "%.2f"|format(exploratory_results.summary.orders.total_sales) if exploratory_results.summary.orders.total_sales else 'N/A' }}</div>
            </div>
            <div class="summary-card">
                <h4>Panier moyen</h4>
                <div class="value">€{{ "%.2f"|format(exploratory_results.summary.orders.avg_order_value) if exploratory_results.summary.orders.avg_order_value else 'N/A' }}</div>
            </div>
            <div class="summary-card">
                <h4>Clients uniques</h4>
                <div class="value">{{ exploratory_results.summary.orders.unique_customers | default('N/A') }}</div>
            </div>
        </div>

        <h3>Visualisations</h3>
        {% if exploratory_results.plots %}
        {% for plot_name, plot_path in exploratory_results.plots.items() %}
        <div class="plot-container">
            <h4>{{ plot_name | title }}</h4>
            <img src="{{ plot_path }}" alt="{{ plot_name }}">
        </div>
        {% endfor %}
        {% endif %}
        {% endif %}

        {% if clustering_results %}
        <h2>🎯 Segmentation Clients (Clustering)</h2>
        
        <h3>Résultats du clustering</h3>
        <div class="summary-grid">
            <div class="summary-card">
                <h4>Nombre de clusters</h4>
                <div class="value">{{ clustering_results.n_clusters }}</div>
            </div>
            <div class="summary-card">
                <h4>Score de silhouette</h4>
                <div class="value">{{ "%.3f"|format(clustering_results.silhouette_score) if clustering_results.silhouette_score else 'N/A' }}</div>
            </div>
        </div>

        {% if clustering_results.cluster_profiles %}
        <h3>Profils des clusters</h3>
        {% for profile in clustering_results.cluster_profiles %}
        <div class="recommendation">
            <strong>Cluster {{ profile.cluster_id }} - {{ profile.profile }}</strong><br>
            <small>{{ profile.n_customers }} clients ({{ "%.1f"|format(profile.percentage) }}%)</small><br>
            <small>CA moyen: €{{ "%.2f"|format(profile.avg_ca_total) }} | Commandes moyennes: {{ "%.1f"|format(profile.avg_nb_commandes) }}</small>
        </div>
        {% endfor %}
        {% endif %}

        <div class="plot-container">
            <img src="results/plots/clustering_analysis.png" alt="Clustering Analysis">
        </div>
        {% endif %}

        {% if anomaly_results %}
        <h2>⚠️ Détection d'Anomalies</h2>
        
        <h3>Statistiques des anomalies</h3>
        <div class="summary-grid">
            <div class="summary-card">
                <h4>Transactions analysées</h4>
                <div class="value">{{ anomaly_results.stats.total_transactions | default('N/A') }}</div>
            </div>
            <div class="summary-card">
                <h4>Anomalies détectées</h4>
                <div class="value">{{ anomaly_results.n_anomalies }}</div>
            </div>
            <div class="summary-card">
                <h4>Taux d'anomalie</h4>
                <div class="value">{{ "%.2f"|format(anomaly_results.anomaly_rate) }}%</div>
            </div>
        </div>

        {% if anomaly_results.anomaly_types %}
        <h3>Types d'anomalies</h3>
        {% for anomaly_type in anomaly_results.anomaly_types %}
        <div class="recommendation">
            <strong>{{ anomaly_type.type }}</strong><br>
            <small>{{ anomaly_type.count }} occurrences - {{ anomaly_type.description }}</small>
        </div>
        {% endfor %}
        {% endif %}

        <div class="plot-container">
            <img src="results/plots/anomaly_detection.png" alt="Anomaly Detection">
        </div>
        {% endif %}

        {% if rfm_results %}
        <h2>📈 Analyse RFM</h2>
        
        <h3>Segments clients</h3>
        <div class="summary-grid">
            <div class="summary-card">
                <h4>Clients analysés</h4>
                <div class="value">{{ rfm_results.n_customers }}</div>
            </div>
            <div class="summary-card">
                <h4>Segments identifiés</h4>
                <div class="value">{{ rfm_results.n_segments }}</div>
            </div>
        </div>

        {% if rfm_results.segments %}
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Segment</th>
                        <th>Nb Clients</th>
                        <th>%</th>
                        <th>CA Moyen</th>
                        <th>Panier Moyen</th>
                    </tr>
                </thead>
                <tbody>
                    {% for segment in rfm_results.segments.itertuples() %}
                    <tr>
                        <td>{{ segment.segment }}</td>
                        <td>{{ segment.n_customers }}</td>
                        <td>{{ "%.1f"|format(segment.percentage) }}%</td>
                        <td>€{{ "%.2f"|format(segment.avg_monetary) }}</td>
                        <td>€{{ "%.2f"|format(segment.avg_order_value) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if rfm_results.recommendations %}
        <h3>Recommandations par segment</h3>
        {% for rec in rfm_results.recommendations %}
        <div class="recommendation">
            <strong>{{ rec.segment }}</strong> ({{ rec.n_customers }} clients)<br>
            <small>{{ rec.recommendation }}</small>
        </div>
        {% endfor %}
        {% endif %}

        <div class="plot-container">
            <img src="results/plots/rfm_analysis.png" alt="RFM Analysis">
        </div>
        {% endif %}

        <h2>💡 Insights Business</h2>
        <div class="highlight">
            <h3>Conclusions clés</h3>
            <ul>
                <li><strong>Performance globale :</strong> Les analyses révèlent des patterns clairs dans le comportement client</li>
                <li><strong>Opportunités :</strong> Plusieurs segments identifiés pour des campagnes marketing ciblées</li>
                <li><strong>Risques :</strong> Anomalies détectées nécessitant une attention particulière</li>
                <li><strong>Actions recommandées :</strong> Mettre en place des stratégies par segment pour optimiser la rétention</li>
            </ul>
        </div>

        <h2>📁 Données exportées</h2>
        <p>Tous les résultats détaillés sont disponibles dans les fichiers CSV suivants :</p>
        <ul>
            <li><code>results/data/orders_summary.csv</code> - Données commandes</li>
            <li><code>results/data/customers_with_clusters.csv</code> - Clients avec clusters</li>
            <li><code>results/data/transactions_with_anomalies.csv</code> - Transactions avec anomalies</li>
            <li><code>results/data/rfm_analysis.csv</code> - Analyse RFM complète</li>
        </ul>

        <div class="footer">
            <p>Rapport généré automatiquement par le pipeline Data Mining - ERP Distribution</p>
            <p>{{ generation_date }}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return Template(template)
    
    def generate_report(self, analyses_results):
        """Générer le rapport HTML complet"""
        
        # Préparer les données pour le template
        template_data = {
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyses': analyses_results
        }
        
        # Ajouter les résultats détaillés si disponibles
        # (Pour l'instant, on utilise les résultats du pipeline)
        
        # Générer le HTML
        html_content = self.template.render(**template_data)
        
        # Sauvegarder le fichier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.results_base_path / 'reports' / f'data_mining_report_{timestamp}.html'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path

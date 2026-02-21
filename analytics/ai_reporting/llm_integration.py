"""
Intégration LLM pour l'ERP Distribution

Module d'intégration avec différents LLM (OpenAI, Claude, etc.)
pour l'analyse avancée et la génération de rapports intelligents.
"""

import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

class LLMIntegration:
    def __init__(self):
        self.conn = get_connection()
        self.providers = {
            'openai': {
                'api_key': os.getenv("OPENAI_API_KEY"),
                'base_url': 'https://api.openai.com/v1',
                'model': 'gpt-3.5-turbo',
                'max_tokens': 4000
            },
            'claude': {
                'api_key': os.getenv("CLAUDE_API_KEY"),
                'base_url': 'https://api.anthropic.com/v1',
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 4000
            },
            'local': {
                'api_key': None,
                'base_url': 'http://localhost:11434/v1',
                'model': 'llama2',
                'max_tokens': 2000
            }
        }
    
    def test_provider_connection(self, provider_name: str) -> bool:
        """Tester la connexion à un provider LLM"""
        
        if provider_name not in self.providers:
            return False
        
        provider = self.providers[provider_name]
        
        if not provider['api_key'] and provider_name != 'local':
            return False
        
        try:
            if provider_name == 'openai':
                headers = {
                    'Authorization': f"Bearer {provider['api_key']}",
                    'Content-Type': 'application/json'
                }
                data = {
                    'model': provider['model'],
                    'messages': [{'role': 'user', 'content': 'Hello'}],
                    'max_tokens': 10
                }
                response = requests.post(f"{provider['base_url']}/chat/completions", 
                                     headers=headers, json=data, timeout=10)
                return response.status_code == 200
            
            elif provider_name == 'claude':
                headers = {
                    'x-api-key': provider['api_key'],
                    'Content-Type': 'application/json',
                    'anthropic-version': '2023-06-01'
                }
                data = {
                    'model': provider['model'],
                    'max_tokens': 10,
                    'messages': [{'role': 'user', 'content': 'Hello'}]
                }
                response = requests.post(f"{provider['base_url']}/messages", 
                                     headers=headers, json=data, timeout=10)
                return response.status_code == 200
            
            elif provider_name == 'local':
                headers = {'Content-Type': 'application/json'}
                data = {
                    'model': provider['model'],
                    'messages': [{'role': 'user', 'content': 'Hello'}],
                    'max_tokens': 10
                }
                response = requests.post(f"{provider['base_url']}/chat/completions", 
                                     headers=headers, json=data, timeout=10)
                return response.status_code == 200
        
        except Exception as e:
            print(f"Erreur test {provider_name}: {e}")
            return False
        
        return False
    
    def get_available_providers(self) -> List[str]:
        """Lister les providers disponibles"""
        
        available = []
        for provider_name, config in self.providers.items():
            if provider_name == 'local':
                # Toujours considérer local comme disponible (pour test)
                available.append(provider_name)
            elif config['api_key']:
                available.append(provider_name)
        
        return available
    
    def call_llm(self, provider_name: str, messages: List[Dict], 
                   temperature: float = 0.7, max_tokens: Optional[int] = None) -> Optional[str]:
        """Appeler un LLM spécifique"""
        
        if provider_name not in self.providers:
            return None
        
        provider = self.providers[provider_name]
        
        if not provider['api_key'] and provider_name != 'local':
            return None
        
        try:
            if provider_name == 'openai':
                return self._call_openai(provider, messages, temperature, max_tokens)
            elif provider_name == 'claude':
                return self._call_claude(provider, messages, temperature, max_tokens)
            elif provider_name == 'local':
                return self._call_local(provider, messages, temperature, max_tokens)
        
        except Exception as e:
            print(f"Erreur appel {provider_name}: {e}")
            return None
    
    def _call_openai(self, provider: Dict, messages: List[Dict], 
                    temperature: float, max_tokens: Optional[int]) -> Optional[str]:
        """Appeler l'API OpenAI"""
        
        headers = {
            'Authorization': f"Bearer {provider['api_key']}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': provider['model'],
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens or provider['max_tokens']
        }
        
        response = requests.post(f"{provider['base_url']}/chat/completions", 
                             headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        
        return None
    
    def _call_claude(self, provider: Dict, messages: List[Dict], 
                    temperature: float, max_tokens: Optional[int]) -> Optional[str]:
        """Appeler l'API Claude"""
        
        headers = {
            'x-api-key': provider['api_key'],
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': provider['model'],
            'max_tokens': max_tokens or provider['max_tokens'],
            'messages': messages
        }
        
        response = requests.post(f"{provider['base_url']}/messages", 
                             headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        
        return None
    
    def _call_local(self, provider: Dict, messages: List[Dict], 
                    temperature: float, max_tokens: Optional[int]) -> Optional[str]:
        """Appeler un LLM local"""
        
        headers = {'Content-Type': 'application/json'}
        
        data = {
            'model': provider['model'],
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens or provider['max_tokens']
        }
        
        response = requests.post(f"{provider['base_url']}/chat/completions", 
                             headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        
        return None
    
    def load_business_context(self) -> Dict:
        """Charger le contexte business pour les requêtes LLM"""
        
        queries = {
            'kpi_summary': """
                SELECT 
                    SUM(fo.total_amount) as total_ca,
                    COUNT(DISTINCT fo.order_key) as total_orders,
                    COUNT(DISTINCT fo.customer_key) as total_customers,
                    AVG(fo.total_amount) as avg_order_value,
                    MIN(dd.full_date) as first_date,
                    MAX(dd.full_date) as last_date
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
            """,
            
            'top_products': """
                SELECT 
                    dp.product_name,
                    dp.product_category,
                    SUM(fol.line_amount) as product_ca,
                    SUM(fol.quantity) as total_quantity
                FROM dwh.dim_product dp
                JOIN dwh.fact_order_lines fol ON dp.product_key = fol.product_key
                GROUP BY dp.product_key, dp.product_name, dp.product_category
                ORDER BY product_ca DESC
                LIMIT 5
            """,
            
            'recent_trends': """
                SELECT 
                    dd.month_name,
                    dd.year_number,
                    SUM(fo.total_amount) as monthly_ca,
                    COUNT(DISTINCT fo.order_key) as monthly_orders
                FROM dwh.fact_orders fo
                JOIN dwh.dim_date dd ON fo.order_date_key = dd.date_key
                WHERE dd.full_date >= CURRENT_DATE - INTERVAL '3 months'
                GROUP BY dd.year_number, dd.month_name
                ORDER BY dd.year_number, dd.month_name
            """
        }
        
        context = {}
        for key, query in queries.items():
            context[key] = pd.read_sql(query, self.conn)
        
        return context
    
    def generate_business_analysis(self, provider_name: str, question: str) -> Optional[str]:
        """Générer une analyse business avec LLM"""
        
        context = self.load_business_context()
        
        # Préparer le contexte pour le LLM
        context_text = f"""
        Contexte Business ERP Distribution:
        
        KPIs Principaux:
        - Chiffre d'affaires total: {context['kpi_summary']['total_ca'].iloc[0]:,.0f} €
        - Commandes totales: {context['kpi_summary']['total_orders'].iloc[0]:,}
        - Clients totaux: {context['kpi_summary']['total_customers'].iloc[0]:,}
        - Panier moyen: {context['kpi_summary']['avg_order_value'].iloc[0]:.0f} €
        - Période: {context['kpi_summary']['first_date'].iloc[0]} au {context['kpi_summary']['last_date'].iloc[0]}
        
        Top 5 Produits:
        {self._format_dataframe(context['top_products'])}
        
        Tendances Récentes (3 derniers mois):
        {self._format_dataframe(context['recent_trends'])}
        
        Question: {question}
        
        Génère une analyse business détaillée et actionnable basée sur ces données.
        """
        
        messages = [
            {'role': 'system', 'content': 'Tu es un expert en analyse business et data science pour une entreprise de distribution ERP.'},
            {'role': 'user', 'content': context_text}
        ]
        
        return self.call_llm(provider_name, messages, temperature=0.3)
    
    def _format_dataframe(self, df: pd.DataFrame) -> str:
        """Formater un DataFrame pour le contexte LLM"""
        
        if df.empty:
            return "Aucune donnée disponible"
        
        return df.to_string(index=False)
    
    def generate_sql_query(self, provider_name: str, natural_language: str) -> Optional[str]:
        """Générer une requête SQL à partir du langage naturel"""
        
        schema_info = """
        Schéma de la base de données ERP Distribution:
        
        Tables principales:
        - dwh.fact_orders (commandes): order_key, customer_key, order_date_key, total_amount
        - dwh.dim_customer (clients): customer_key, customer_name, email
        - dwh.dim_product (produits): product_key, product_name, product_category, unit_price
        - dwh.fact_order_lines (lignes commandes): order_line_key, order_key, product_key, quantity, unit_price
        - dwh.dim_date (dates): date_key, full_date, month_name, year_number
        - dwh.dim_geography (géographie): geography_key, country, region, city
        """
        
        messages = [
            {'role': 'system', 'content': f'Tu es un expert SQL. {schema_info}'},
            {'role': 'user', 'content': f'Génère une requête SQL PostgreSQL pour: {natural_language}'}
        ]
        
        return self.call_llm(provider_name, messages, temperature=0.1)
    
    def generate_dashboard_insights(self, provider_name: str, dashboard_data: Dict) -> Optional[str]:
        """Générer des insights pour un dashboard spécifique"""
        
        messages = [
            {'role': 'system', 'content': 'Tu es un expert en data visualization et business intelligence.'},
            {'role': 'user', 'content': f'''
            Analyse les données du dashboard suivantes et génère 3 insights business clés:
            
            Données: {json.dumps(dashboard_data, indent=2)}
            
            Pour chaque insight, fournis:
            1. Un titre accrocheur
            2. La tendance ou anomalie identifiée
            3. L'impact business potentiel
            4. Une recommandation actionnable
            
            Format de réponse structuré avec des émojis pour chaque insight.
            '''}
        ]
        
        return self.call_llm(provider_name, messages, temperature=0.6)
    
    def test_all_providers(self):
        """Tester tous les providers disponibles"""
        
        print("🔍 Test des providers LLM disponibles...")
        
        available = self.get_available_providers()
        results = {}
        
        for provider in available:
            print(f"  Test de {provider}...")
            is_working = self.test_provider_connection(provider)
            results[provider] = is_working
            
            status = "✅" if is_working else "❌"
            print(f"  {status} {provider}: {'Fonctionnel' if is_working else 'Non fonctionnel'}")
        
        return results
    
    def interactive_llm_session(self, provider_name: str):
        """Session interactive avec un LLM"""
        
        if provider_name not in self.get_available_providers():
            print(f"❌ Provider {provider_name} non disponible")
            return
        
        print(f"\n🤖 Session interactive avec {provider_name.upper()}")
        print("Tape 'quit' pour quitter, 'help' pour l'aide")
        print("-" * 50)
        
        context = self.load_business_context()
        
        while True:
            try:
                user_input = input("\n👤 Vous: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Au revoir!")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif not user_input:
                    continue
                
                print("🤖 LLM: ", end="")
                
                # Ajouter le contexte business
                context_prompt = f"""
                Contexte business ERP Distribution:
                - CA total: {context['kpi_summary']['total_ca'].iloc[0]:,.0f} €
                - Clients: {context['kpi_summary']['total_customers'].iloc[0]:,}
                - Produits: {len(context['top_products'])}
                
                Question: {user_input}
                """
                
                messages = [
                    {'role': 'system', 'content': 'Tu es un assistant business pour ERP Distribution.'},
                    {'role': 'user', 'content': context_prompt}
                ]
                
                response = self.call_llm(provider_name, messages)
                if response:
                    print(response)
                else:
                    print("❌ Erreur de réponse du LLM")
            
            except KeyboardInterrupt:
                print("\n👋 Session interrompue")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    def show_help(self):
        """Afficher l'aide de la session interactive"""
        
        help_text = """
        📚 Aide - Session LLM Interactive
        
        Commandes disponibles:
        • help - Afficher cette aide
        • quit - Quitter la session
        
        Exemples de questions:
        • "Quels sont les produits les plus rentables?"
        • "Analyse la performance des ventes du dernier mois"
        • "Génère une requête SQL pour les clients VIP"
        • "Quelles recommandations pour augmenter le CA?"
        • "Analyse les tendances géographiques"
        """
        
        print(help_text)
    
    def close(self):
        """Fermer la connexion"""
        self.conn.close()

def main():
    """Fonction principale"""
    print("🚀 Lancement de l'intégration LLM...")
    
    llm = LLMIntegration()
    
    try:
        # Tester les providers
        results = llm.test_all_providers()
        
        # Session interactive avec le premier provider disponible
        available = llm.get_available_providers()
        if available:
            provider = available[0]
            print(f"\n🎯 Lancement session interactive avec {provider}")
            llm.interactive_llm_session(provider)
        else:
            print("❌ Aucun provider LLM disponible")
            print("Configurez OPENAI_API_KEY ou CLAUDE_API_KEY dans .env")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        llm.close()

if __name__ == "__main__":
    main()

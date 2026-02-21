"""
Explorateur Data Warehouse - Script Python pour visualiser la structure
"""

import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv("olap/configs/.env")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("OLAP_PGHOST", "localhost"),
        port=int(os.getenv("OLAP_PGPORT", "5432")),
        dbname=os.getenv("OLAP_PGDATABASE"),
        user=os.getenv("OLAP_PGUSER"),
        password=os.getenv("OLAP_PGPASSWORD"),
    )

def explore_data_warehouse():
    """Explorer complètement le Data Warehouse"""
    
    print("🔍 EXPLORATION DATA WAREHOUSE")
    print("=" * 50)
    
    conn = get_connection()
    
    try:
        # 1. Lister toutes les tables
        print("\n📋 TABLES DU DATA WAREHOUSE:")
        tables_query = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'dwh' 
        ORDER BY table_name
        """
        
        tables_df = pd.read_sql(tables_query, conn)
        print(tables_df.to_string(index=False))
        
        # 2. Statistiques des tables principales
        print("\n📊 STATISTIQUES TABLES PRINCIPALES:")
        
        main_tables = [
            'dim_customer', 'dim_product', 'dim_date', 'dim_geography',
            'fact_sales_order_line', 'fact_order_status_transition', 'fact_inventory_snapshot'
        ]
        
        for table in main_tables:
            try:
                count_query = f"SELECT COUNT(*) as total_rows FROM dwh.{table}"
                result = pd.read_sql(count_query, conn)
                row_count = result['total_rows'].iloc[0]
                print(f"  • {table}: {row_count:,} lignes")
            except:
                print(f"  • {table}: Non trouvée")
        
        # 3. Structure des tables de dimension
        print("\n🏗️ STRUCTURE DIMENSIONS:")
        
        dim_tables = ['dim_customer', 'dim_product', 'dim_geography', 'dim_date']
        
        for table in dim_tables:
            try:
                struct_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'dwh' AND table_name = '{table}'
                ORDER BY ordinal_position
                """
                struct_df = pd.read_sql(struct_query, conn)
                print(f"\n  📋 {table}:")
                for _, row in struct_df.iterrows():
                    nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"    - {row['column_name']}: {row['data_type']} ({nullable})")
            except Exception as e:
                print(f"  ❌ Erreur {table}: {e}")
        
        # 4. Structure des tables de faits
        print("\n⚡ STRUCTURE TABLES DE FAITS:")
        
        fact_tables = ['fact_sales_order_line', 'fact_order_status_transition']
        
        for table in fact_tables:
            try:
                struct_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'dwh' AND table_name = '{table}'
                ORDER BY ordinal_position
                """
                struct_df = pd.read_sql(struct_query, conn)
                print(f"\n  ⚡ {table}:")
                for _, row in struct_df.iterrows():
                    nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"    - {row['column_name']}: {row['data_type']} ({nullable})")
            except Exception as e:
                print(f"  ❌ Erreur {table}: {e}")
        
        # 5. Aperçu des données
        print("\n👁️  APERÇU DONNÉES:")
        
        # Customers
        try:
            customers_query = "SELECT * FROM dwh.dim_customer LIMIT 5"
            customers_df = pd.read_sql(customers_query, conn)
            print(f"\n  👥 Clients (5 premiers):")
            print(customers_df[['customer_key', 'customer_name', 'segment', 'city']].to_string(index=False))
        except Exception as e:
            print(f"  ❌ Erreur clients: {e}")
        
        # Products
        try:
            products_query = "SELECT * FROM dwh.dim_product LIMIT 5"
            products_df = pd.read_sql(products_query, conn)
            print(f"\n  📦 Produits (5 premiers):")
            print(products_df[['product_key', 'product_name', 'category', 'price']].to_string(index=False))
        except Exception as e:
            print(f"  ❌ Erreur produits: {e}")
        
        # Sales orders
        try:
            sales_query = """
            SELECT order_id, customer_key, product_key, sales_amount, quantity 
            FROM dwh.fact_sales_order_line 
            LIMIT 5
            """
            sales_df = pd.read_sql(sales_query, conn)
            print(f"\n  💰 Commandes (5 premières):")
            print(sales_df.to_string(index=False))
        except Exception as e:
            print(f"  ❌ Erreur commandes: {e}")
        
        # 6. Requêtes d'analyse rapide
        print("\n📈 ANALYSES RAPIDES:")
        
        # Top clients
        try:
            top_clients_query = """
            SELECT dc.customer_name, SUM(fol.sales_amount) as total_ca, COUNT(fol.order_id) as nb_orders
            FROM dwh.fact_sales_order_line fol
            JOIN dwh.dim_customer dc ON fol.customer_key = dc.customer_key
            GROUP BY dc.customer_name
            ORDER BY total_ca DESC
            LIMIT 5
            """
            top_clients_df = pd.read_sql(top_clients_query, conn)
            print(f"\n  🏆 Top 5 clients par CA:")
            for _, row in top_clients_df.iterrows():
                print(f"    {row['customer_name']}: {row['total_ca']:.0f}€ ({row['nb_orders']} commandes)")
        except Exception as e:
            print(f"  ❌ Erreur top clients: {e}")
        
        # Top produits
        try:
            top_products_query = """
            SELECT dp.product_name, dp.category, SUM(fol.sales_amount) as total_ca, SUM(fol.quantity) as total_qty
            FROM dwh.fact_sales_order_line fol
            JOIN dwh.dim_product dp ON fol.product_key = dp.product_key
            GROUP BY dp.product_name, dp.category
            ORDER BY total_ca DESC
            LIMIT 5
            """
            top_products_df = pd.read_sql(top_products_query, conn)
            print(f"\n  📦 Top 5 produits par CA:")
            for _, row in top_products_df.iterrows():
                print(f"    {row['product_name']}: {row['total_ca']:.0f}€ ({row['total_qty']} unités)")
        except Exception as e:
            print(f"  ❌ Erreur top produits: {e}")
        
        print(f"\n✅ Exploration Data Warehouse terminée!")
        
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    explore_data_warehouse()

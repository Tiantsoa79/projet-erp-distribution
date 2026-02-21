#!/usr/bin/env python3
"""
Pipeline Data Mining - ERP Distribution

Exécute l'ensemble des analyses de Data Mining sur le Data Warehouse.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Ajouter le répertoire courant au path
MINING_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MINING_DIR.parent
sys.path.append(str(MINING_DIR))

from exploratory_analysis import ExploratoryAnalysis
from clustering_analysis import ClusteringAnalysis
from anomaly_detection import AnomalyDetection
from rfm_analysis import RFMAnalysis
from report_generator import ReportGenerator

# Charger la configuration (.env racine en priorite, sinon local)
_env = PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else MINING_DIR / ".env"
load_dotenv(_env)

def get_dwh_connection():
    """Connexion au Data Warehouse"""
    return psycopg2.connect(
        host=os.getenv("DWH_PGHOST", "localhost"),
        port=int(os.getenv("DWH_PGPORT", "5432")),
        database=os.getenv("DWH_PGDATABASE"),
        user=os.getenv("DWH_PGUSER"),
        password=os.getenv("DWH_PGPASSWORD"),
    )

def ensure_results_dirs():
    """Créer les répertoires de résultats"""
    base_path = Path(os.getenv("MINING_RESULTS_PATH", "results"))
    for subdir in ["plots", "reports", "data"]:
        (base_path / subdir).mkdir(parents=True, exist_ok=True)

def print_header():
    """Afficher l'en-tête du pipeline"""
    print("=" * 80)
    print("  DATA MINING PIPELINE  |  ERP Distribution")
    print("=" * 80)
    print(f"Début : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_summary(results):
    """Afficher le résumé des analyses"""
    print("\n" + "=" * 80)
    print("  RÉSUMÉ DES ANALYSES DATA MINING")
    print("=" * 80)
    
    for analysis, result in results.items():
        status = "[OK] Succès" if result.get("success", False) else "[ERREUR]"
        print(f"{analysis:25} : {status}")
        if result.get("message"):
            print(f"{'':27}   {result['message']}")
    
    print(f"\nTerminé : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Rapport HTML : results/reports/data_mining_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

def main():
    """Fonction principale du pipeline Data Mining"""
    parser = argparse.ArgumentParser(description="Pipeline Data Mining ERP Distribution")
    parser.add_argument("--analysis", choices=["exploratory", "clustering", "anomaly", "rfm", "all"], 
                       default="all", help="Type d'analyse à exécuter")
    parser.add_argument("--quick", action="store_true", help="Mode rapide (échantillon de données)")
    args = parser.parse_args()
    
    print_header()
    
    # Créer les répertoires de résultats
    ensure_results_dirs()
    
    # Connexion à la base
    try:
        conn = get_dwh_connection()
        print("[OK] Connexion au Data Warehouse etablie")
    except Exception as e:
        print(f"[ERREUR] Erreur de connexion au Data Warehouse : {e}")
        return 1
    
    # Résultats des analyses
    results = {}
    
    try:
        # 1. Analyse exploratoire
        if args.analysis in ["exploratory", "all"]:
            print("\n--- 1. Analyse Exploratoire ---")
            try:
                ea = ExploratoryAnalysis(conn)
                ea_results = ea.run(quick=args.quick)
                results["Exploratoire"] = {"success": True, "message": f"{ea_results['summary']['orders']['total_records']} enregistrements analysés"}
                print("[OK] Analyse exploratoire terminee")
            except Exception as e:
                results["Exploratoire"] = {"success": False, "message": str(e)}
                print(f"[ERREUR] Erreur analyse exploratoire : {e}")
        
        # 2. Clustering clients
        if args.analysis in ["clustering", "all"]:
            print("\n--- 2. Clustering Clients ---")
            try:
                ca = ClusteringAnalysis(conn)
                ca_results = ca.run(quick=args.quick)
                results["Clustering"] = {"success": True, "message": f"{ca_results['n_clusters']} clusters identifies"}
                print("[OK] Clustering termine")
            except Exception as e:
                results["Clustering"] = {"success": False, "message": str(e)}
                print(f"[ERREUR] Erreur clustering : {e}")
        
        # 3. Détection d'anomalies
        if args.analysis in ["anomaly", "all"]:
            print("\n--- 3. Détection d'Anomalies ---")
            try:
                ad = AnomalyDetection(conn)
                ad_results = ad.run(quick=args.quick)
                results["Anomalies"] = {"success": True, "message": f"{ad_results['n_anomalies']} anomalies detectees"}
                print("[OK] Détection d'anomalies terminee")
            except Exception as e:
                results["Anomalies"] = {"success": False, "message": str(e)}
                print(f"[ERREUR] Erreur détection anomalies : {e}")
        
        # 4. Analyse RFM
        if args.analysis in ["rfm", "all"]:
            print("\n--- 4. Analyse RFM ---")
            try:
                rfm = RFMAnalysis(conn)
                rfm_results = rfm.run(quick=args.quick)
                results["RFM"] = {"success": True, "message": f"{len(rfm_results['segments'])} segments RFM crees"}
                print("[OK] Analyse RFM terminee")
            except Exception as e:
                results["RFM"] = {"success": False, "message": str(e)}
                print(f"[ERREUR] Erreur analyse RFM : {e}")
        
        # 5. Génération du rapport HTML
        print("\n--- 5. Génération du Rapport ---")
        try:
            rg = ReportGenerator()
            report_path = rg.generate_report(results)
            results["Rapport"] = {"success": True, "message": f"Rapport genere : {report_path}"}
            print("[OK] Rapport HTML genere")
        except Exception as e:
            results["Rapport"] = {"success": False, "message": str(e)}
            print(f"[ERREUR] Erreur generation rapport : {e}")
    
    finally:
        conn.close()
    
    # Afficher le résumé
    print_summary(results)
    
    return 0 if all(r.get("success", False) for r in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())

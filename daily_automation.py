#!/usr/bin/env python3
"""
Automatisation Quotidienne Simplifiée - ERP Distribution
====================================================

Exécute les analyses tous les jours à heure fixe.
Idéal pour un usage quotidien avec peu de changements.

Usage :
    python daily_automation.py            # Exécution immédiate
    python daily_automation.py --schedule  # Mode planifié (toutes les 24h)
"""

import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import run, PIPE

# Configuration
ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
LOG_FILE = ROOT / "daily_automation.log"

# Configuration du logging avec rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            LOG_FILE, 
            maxBytes=10*1024*1024,  # 10MB max
            backupCount=5,  # Garder 5 fichiers de backup
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log(message):
    """Logger utilisant le module logging"""
    logger.info(message)

def run_component(name, command):
    """Exécute un composant et retourne le succès"""
    log(f"Démarrage {name}...")
    
    try:
        result = run(
            command,
            cwd=str(ROOT),
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            log(f"✅ {name} terminé avec succès")
            return True
        else:
            log(f"❌ {name} échoué: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        log(f"❌ {name} erreur: {e}")
        return False

def check_data_changes():
    """Vérification simple des changements via l'ETL"""
    log("Vérification des changements...")
    
    # Exécuter l'ETL en mode détection SEULEMENT
    result = run(
        "python BI/run_pipeline.py --check-only",
        cwd=str(ROOT),
        shell=True,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    # Si --check-only n'existe pas, utiliser l'ancienne méthode mais éviter double exécution
    if result.returncode != 0 or "--check-only" not in result.stderr:
        log("⚠️ Mode --check-only non supporté, utilisation de la détection standard")
        result = run(
            "python BI/run_pipeline.py --dry-run",
            cwd=str(ROOT),
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Si --dry-run n'existe pas non plus, on utilise l'ETL normal mais on évite Data Mining dupliqué
        if result.returncode != 0 or "--dry-run" not in result.stderr:
            log("📊 Exécution ETL complète (aucun mode détection disponible)")
            etl_result = run(
                "python BI/run_pipeline.py",
                cwd=str(ROOT),
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Analyser la sortie pour détecter les changements
            output = etl_result.stdout + etl_result.stderr
            
            if "Changements detectes" in output:
                log("🔄 Changements détectés dans les données")
                return "etl_done_with_changes"
            elif "Aucun changement detecte" in output:
                log("✅ Aucun changement, analyses non nécessaires")
                return "etl_done_no_changes"
            else:
                log("⚠️ Impossible de déterminer les changements, exécution quand même")
                return "etl_done_unknown"
    
    # Analyser la sortie pour détecter les changements (mode --check-only ou --dry-run)
    output = result.stdout + result.stderr
    
    if "Changements detectes" in output:
        log("🔄 Changements détectés dans les données")
        return True
    elif "Aucun changement detecte" in output:
        log("✅ Aucun changement, analyses non nécessaires")
        return False
    else:
        log("⚠️ Impossible de déterminer les changements, exécution quand même")
        return True  # Au cas où, on exécute quand même

def run_daily_analysis():
    """Exécute le pipeline quotidien complet"""
    log("=" * 60)
    log("AUTOMATISATION QUOTIDIENNE - ERP Distribution")
    log("=" * 60)
    
    # Charger l'environnement
    if ENV_FILE.exists():
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE, override=True)
        log("Configuration .env chargée")
    else:
        log("⚠️ Fichier .env non trouvé")
    
    # 1. Vérifier les changements
    changes_status = check_data_changes()
    
    # Gérer les différents retours de check_data_changes
    if changes_status == "etl_done_no_changes":
        log("Pipeline terminé - aucun changement à traiter")
        return True
    elif changes_status == "etl_done_with_changes":
        log("🔄 ETL terminé avec changements, passage aux analyses...")
        # ETL déjà fait, on passe directement aux analyses
    elif changes_status == "etl_done_unknown":
        log("⚠️ ETL terminé avec statut inconnu, exécution des analyses...")
    elif changes_status is False:
        log("✅ Aucun changement détecté, pipeline terminé")
        return True
    else:
        # True = changements détectés, ETL pas encore fait
        log("🔄 Changements détectés, exécution ETL...")
        etl_success = run_component(
            "ETL Pipeline", 
            "python BI/run_pipeline.py"
        )
        if not etl_success:
            log("❌ ETL échoué, arrêt du pipeline")
            return False
    
    # 2. Data Mining (si changements et ETL réussi)
    mining_success = run_component(
        "Data Mining", 
        "python data_mining/run_mining.py --analysis all"
    )
    
    # 3. AI Reporting (si Data Mining a réussi)
    if mining_success:
        ai_success = run_component(
            "AI Reporting",
            "python ai-reporting/run_reporting.py --json"
        )
    else:
        log("⏭️ AI Reporting ignoré (Data Mining échoué)")
        ai_success = False
    
    # 4. Résumé
    log("=" * 60)
    log("RÉSUMÉ QUOTIDIEN:")
    log(f"  Changements détectés : {'OUI' if has_changes else 'NON'}")
    log(f"  Data Mining : {'✅ SUCCÈS' if mining_success else '❌ ÉCHEC'}")
    log(f"  AI Reporting : {'✅ SUCCÈS' if ai_success else '❌ ÉCHEC'}")
    log("=" * 60)
    
    return mining_success and ai_success

def schedule_daily():
    """Mode planification toutes les 24h"""
    log("Démarrage mode planification (toutes les 24h à 2h du matin)")
    
    while True:
        try:
            # Calculer la prochaine exécution à 2h du matin
            now = datetime.now()
            
            # Si on est avant 2h aujourd'hui, exécuter aujourd'hui à 2h
            if now.hour < 2:
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            else:
                # Sinon, exécuter demain à 2h
                next_run = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
            
            sleep_seconds = (next_run - now).total_seconds()
            log(f"Prochaine exécution le {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Dormir par heures pour pouvoir interrompre
            hours_to_wait = int(sleep_seconds / 3600)
            for hour in range(hours_to_wait):
                time.sleep(3600)  # 1 heure
                remaining = hours_to_wait - hour - 1
                if remaining > 0:
                    log(f"Attente... {remaining}h restantes")
                else:
                    log("⏰ Exécution imminente...")
            
            # Exécuter l'analyse quotidienne
            success = run_daily_analysis()
            
            # Petite pause après l'exécution pour éviter double exécution
            time.sleep(60)  # 1 minute
                
        except KeyboardInterrupt:
            log("\nArrêt demandé par l'utilisateur")
            break
        except Exception as e:
            log(f"Erreur dans la planification: {e}")
            time.sleep(3600)  # Attendre 1h avant de réessayer

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Automatisation quotidienne ERP Distribution")
    parser.add_argument("--schedule", action="store_true", 
                       help="Mode planification (toutes les 24h)")
    args = parser.parse_args()
    
    if args.schedule:
        schedule_daily()
    else:
        success = run_daily_analysis()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

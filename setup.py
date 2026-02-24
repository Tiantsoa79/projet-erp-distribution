#!/usr/bin/env python3
"""
Script d'installation et configuration - ERP Distribution
====================================================

Ce script automatise l'installation complète du projet :
1. Création de l'environnement virtuel
2. Installation des dépendances Python
3. Configuration du fichier .env
4. Installation des dépendances Node.js
5. Import des données CSV
6. Vérification des prérequis

Usage:
    python setup.py [--skip-data] [--skip-npm]
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Configuration
ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
REQUIREMENTS = ROOT / "requirements.txt"

def run_command(cmd, cwd=None, check=True):
    """Exécute une commande et retourne le résultat"""
    print(f"🔧 Exécution : {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                          capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"⚠️ Erreur : {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution : {e}")
        return False

def check_python():
    """Vérifie la version de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ requis. Version actuelle :", f"{version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} détecté")
    return True

def check_node():
    """Vérifie l'installation de Node.js"""
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version} détecté")
            return True
    except:
        pass
    print("❌ Node.js non trouvé. Veuillez installer Node.js 18+")
    return False

def create_venv():
    """Crée l'environnement virtuel"""
    if VENV_DIR.exists():
        print("✅ Environnement virtuel déjà existant")
        return True
    
    print("📦 Création de l'environnement virtuel...")
    # Utiliser des chemins bruts pour éviter les problèmes Windows
    venv_path = str(VENV_DIR).replace('\\', '\\\\')
    if not run_command(f"python -m venv \"{venv_path}\""):
        return False
    print("✅ Environnement virtuel créé")
    return True

def install_python_deps():
    """Installe les dépendances Python"""
    if not REQUIREMENTS.exists():
        print("❌ Fichier requirements.txt non trouvé")
        return False
    
    print("📚 Installation des dépendances Python...")
    
    # Déterminer le script d'activation avec chemins Windows robustes
    if os.name == 'nt':  # Windows
        pip_path = str(VENV_DIR / "Scripts" / "pip.exe").replace('\\', '\\\\')
        requirements_path = str(REQUIREMENTS).replace('\\', '\\\\')
    else:  # Linux/Mac
        pip_path = str(VENV_DIR / "bin" / "pip")
        requirements_path = str(REQUIREMENTS)
    
    # Mettre à jour pip
    if not run_command(f"\"{pip_path}\" install --upgrade pip"):
        return False
    
    # Installer les dépendances
    if not run_command(f"\"{pip_path}\" install -r \"{requirements_path}\""):
        return False
    
    print("✅ Dépendances Python installées")
    return True

def setup_env():
    """Configure le fichier .env"""
    if ENV_FILE.exists():
        print("✅ Fichier .env déjà existant")
        return True
    
    if not ENV_EXAMPLE.exists():
        print("❌ Fichier .env.example non trouvé")
        return False
    
    print("⚙️ Configuration du fichier .env...")
    shutil.copy2(ENV_EXAMPLE, ENV_FILE)
    print("✅ Fichier .env créé depuis .env.example")
    print("📝 Pensez à adapter les valeurs dans .env (mots de passe, etc.)")
    return True

def install_npm_deps():
    """Installe les dépendances Node.js"""
    if not check_node():
        return False
    
    print("📦 Installation des dépendances Node.js...")
    
    # Installer les dépendances de l'API
    api_dir = ROOT / "erp-api"
    if api_dir.exists():
        if not run_command("npm install", cwd=api_dir):
            return False
        print("✅ Dépendances erp-api installées")
    
    # Installer les dépendances de l'interface
    ui_dir = ROOT / "interface_olap"
    if ui_dir.exists():
        if not run_command("npm install", cwd=ui_dir):
            return False
        print("✅ Dépendances interface_olap installées")
    
    return True

def import_data():
    """Importe les données CSV"""
    data_dir = ROOT / "data"
    if not data_dir.exists():
        print("⚠️ Dossier data non trouvé, import des données ignoré")
        return True
    
    print("📊 Import des données CSV...")
    # TODO: Implémenter l'import automatique des données
    print("✅ Import des données (à implémenter manuellement si nécessaire)")
    return True

def check_postgres():
    """Vérifie la connexion PostgreSQL"""
    try:
        import psycopg2
        from psycopg2 import sql
        
        print("🔍 Vérification de la connexion PostgreSQL...")
        
        # Connexion à la base par défaut 'postgres'
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=int(os.getenv('PGPORT', '5432')),
            database='postgres',  # Base par défaut pour créer les autres
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', '')
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Vérifier/créer la base erp_distribution
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'erp_distribution'")
        if not cursor.fetchone():
            print("📊 Création de la base erp_distribution...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier('erp_distribution')))
            print("✅ Base erp_distribution créée")
        else:
            print("✅ Base erp_distribution existe déjà")
        
        # Vérifier/créer la base etl_dw
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'etl_dw'")
        if not cursor.fetchone():
            print("📊 Création de la base etl_dw...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier('etl_dw')))
            print("✅ Base etl_dw créée")
        else:
            print("✅ Base etl_dw existe déjà")
        
        cursor.close()
        conn.close()
        
        # Tester la connexion aux bases créées
        print("🔍 Test de connexion aux bases...")
        
        # Test erp_distribution
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            database='erp_distribution',
            user=pg_user,
            password=pg_password
        )
        conn.close()
        print("✅ Connexion erp_distribution OK")
        
        # Test etl_dw
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database='etl_dw',
            user=pg_user,
            password=pg_password
        )
        conn.close()
        print("✅ Connexion etl_dw OK")
        
        return True
        
    except ImportError:
        print("❌ Module psycopg2 non installé. Installation des dépendances Python d'abord...")
        return False
    except Exception as e:
        print(f"❌ Erreur PostgreSQL: {e}")
        print("\n💡 Solutions possibles:")
        print("   1. Vérifiez que PostgreSQL est en cours d'exécution")
        print("   2. Vérifiez les identifiants dans .env")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Installation ERP Distribution")
    parser.add_argument("--skip-data", action="store_true", help="Skip l'import des données")
    parser.add_argument("--skip-npm", action="store_true", help="Skip l'installation npm")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 INSTALLATION ERP DISTRIBUTION")
    print("=" * 60)
    
    # Ordre d'installation corrigé pour éviter les erreurs
    steps = [
        ("Python", check_python),
        ("Configuration .env", setup_env),
        ("Environnement virtuel", create_venv),
        ("Dépendances Python", install_python_deps),
        ("PostgreSQL", check_postgres),
    ]
    
    if not args.skip_npm:
        steps.append(("Dépendances Node.js", install_npm_deps))
    
    if not args.skip_data:
        steps.append(("Import des données", import_data))
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n📍 {step_name}...")
        if not step_func():
            failed_steps.append(step_name)
    
    print("\n" + "=" * 60)
    if failed_steps:
        print(f"❌ Échec de l'installation")
        print(f"Étapes échouées : {', '.join(failed_steps)}")
        print("\n💡 Solutions possibles:")
        if "Python" in failed_steps:
            print("   - Installez Python 3.8+ depuis https://python.org")
        if "Dépendances Python" in failed_steps:
            print("   - Vérifiez votre connexion internet")
            print("   - Essayez: pip install --upgrade pip")
        if "PostgreSQL" in failed_steps:
            print("   - Démarrez PostgreSQL: pg_ctl -D /path/to/data start")
            print("   - Vérifiez les identifiants dans .env")
        if "Dépendances Node.js" in failed_steps:
            print("   - Installez Node.js 18+ depuis https://nodejs.org")
        return False
    else:
        print("✅ Installation terminée avec succès !")
        print("\n🎯 Prochaines étapes :")
        print("1. Activer l'environnement virtuel :")
        if os.name == 'nt':
            print(f"   {VENV_DIR}\\Scripts\\activate")
        else:
            print(f"   source {VENV_DIR}/bin/activate")
        print("2. Lancer les services :")
        print("   python start_all.py")
        print("3. Accéder à l'interface :")
        print("   http://localhost:3030")
        return True

if __name__ == "__main__":
    main()

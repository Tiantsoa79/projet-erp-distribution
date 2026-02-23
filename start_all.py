#!/usr/bin/env python3
"""
Script de lancement global - ERP Distribution
===============================================

Lance tous les composants du systeme :
  1. ERP API (gateway + micro-services)
  2. Interface OLAP (frontend decisionnelle)

L'automatisation quotidienne (ETL + Data Mining + AI Reporting) 
s'execute via daily_automation.py.

Usage :
    python start_all.py            # Lancer API + Interface
    python start_all.py --api      # ERP API uniquement
    python start_all.py --ui       # Interface OLAP uniquement

Prerequis :
    - Node.js >= 18
    - PostgreSQL en cours d'execution
    - Fichier .env configure a la racine
"""

import os
import sys
import signal
import subprocess
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"

# Couleurs console
class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def banner():
    print(f"""
{C.BOLD}{C.BLUE}================================================================
  ERP Distribution - Lancement global
================================================================{C.END}
""")


def check_env():
    """Verifie que le fichier .env existe."""
    if not ENV_FILE.exists():
        example = ROOT / ".env.example"
        if example.exists():
            print(f"{C.YELLOW}[WARN] .env introuvable. Copie de .env.example...{C.END}")
            import shutil
            shutil.copy(str(example), str(ENV_FILE))
            print(f"{C.GREEN}[OK] .env cree depuis .env.example{C.END}")
            print(f"{C.YELLOW}     Pensez a adapter les valeurs dans .env{C.END}")
        else:
            print(f"{C.RED}[ERREUR] Ni .env ni .env.example trouve a la racine.{C.END}")
            sys.exit(1)


def check_postgres():
    """Vérifie que PostgreSQL est en cours d'exécution et accessible."""
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        # Charger l'environnement
        if ENV_FILE.exists():
            load_dotenv(ENV_FILE)
        
        # Tenter la connexion
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=int(os.getenv('PGPORT', '5432')),
            database=os.getenv('PGDATABASE', 'erp_distribution'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', ''),
            connect_timeout=5
        )
        conn.close()
        print(f"{C.GREEN}[OK] PostgreSQL accessible{C.END}")
        return True
    except psycopg2.OperationalError as e:
        print(f"{C.RED}[ERREUR] PostgreSQL inaccessible : {e}{C.END}")
        print(f"{C.YELLOW}  Solutions possibles :{C.END}")
        print(f"{C.YELLOW}  1. Vérifiez que PostgreSQL est démarré{C.END}")
        print(f"{C.YELLOW}  2. Vérifiez les identifiants dans .env (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD){C.END}")
        print(f"{C.YELLOW}  3. Vérifiez que la base de données existe{C.END}")
        return False
    except ImportError:
        print(f"{C.RED}[ERREUR] psycopg2 non installé. Exécutez : pip install psycopg2-binary{C.END}")
        return False
    except Exception as e:
        print(f"{C.RED}[ERREUR] Erreur inattendue PostgreSQL : {e}{C.END}")
        return False


def check_node():
    """Verifie que Node.js est installe."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        version = result.stdout.strip()
        print(f"{C.GREEN}[OK] Node.js {version}{C.END}")
        return True
    except Exception:
        print(f"{C.RED}[ERREUR] Node.js non trouve. Installez Node.js >= 18.{C.END}")
        return False


def check_npm_deps(directory, name):
    """Verifie que les node_modules sont installes."""
    node_modules = directory / "node_modules"
    if not node_modules.exists():
        print(f"{C.YELLOW}[INFO] Installation des dependances {name}...{C.END}")
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(directory),
            capture_output=True, text=True,
            shell=True,
        )
        if result.returncode != 0:
            print(f"{C.RED}[ERREUR] npm install a echoue pour {name}{C.END}")
            print(result.stderr[:500])
            return False
        print(f"{C.GREEN}[OK] Dependances {name} installees{C.END}")
    return True


def start_erp_api():
    """Lance l'ERP API (gateway + services)."""
    api_dir = ROOT / "erp-api"
    script = api_dir / "scripts" / "start-all.js"

    if not script.exists():
        print(f"{C.RED}[ERREUR] Script erp-api non trouve: {script}{C.END}")
        return None

    if not check_npm_deps(api_dir, "erp-api"):
        return None

    print(f"{C.BLUE}[START] ERP API (gateway + micro-services)...{C.END}")
    proc = subprocess.Popen(
        ["node", str(script)],
        cwd=str(api_dir),
        env={**os.environ, "DOTENV_CONFIG_PATH": str(ENV_FILE)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def start_interface():
    """Lance l'interface OLAP."""
    ui_dir = ROOT / "interface_olap"
    script = ui_dir / "server.js"

    if not script.exists():
        print(f"{C.RED}[ERREUR] Script interface non trouve: {script}{C.END}")
        return None

    if not check_npm_deps(ui_dir, "interface_olap"):
        return None

    print(f"{C.BLUE}[START] Interface OLAP (decisionnelle)...{C.END}")
    proc = subprocess.Popen(
        ["node", str(script)],
        cwd=str(ui_dir),
        env={**os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def stream_output(proc, name):
    """Lit une ligne de sortie du processus (non-bloquant)."""
    if proc and proc.stdout:
        try:
            line = proc.stdout.readline()
            if line:
                text = line.decode("utf-8", errors="replace").rstrip()
                print(f"  [{name}] {text}")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Lancement global ERP Distribution")
    parser.add_argument("--api", action="store_true", help="ERP API uniquement")
    parser.add_argument("--ui", action="store_true", help="Interface OLAP uniquement")
    args = parser.parse_args()

    # Si aucun flag, tout lancer
    launch_api = args.api or (not args.api and not args.ui)
    launch_ui = args.ui or (not args.api and not args.ui)

    banner()
    check_env()

    if not check_node():
        sys.exit(1)
    
    if not check_postgres():
        sys.exit(1)

    processes = {}

    # 1. ERP API
    if launch_api:
        proc = start_erp_api()
        if proc:
            processes["erp-api"] = proc
            time.sleep(2)

    # 2. Interface OLAP
    if launch_ui:
        proc = start_interface()
        if proc:
            processes["interface"] = proc
            time.sleep(1)

    if not processes:
        print(f"{C.RED}[ERREUR] Aucun composant demarre.{C.END}")
        sys.exit(1)

    # Afficher les URLs
    print(f"\n{C.BOLD}{C.GREEN}================================================================")
    print(f"  Composants actifs :")
    if "erp-api" in processes:
        port = os.environ.get("GATEWAY_PORT", "4000")
        print(f"    ERP API Gateway : http://localhost:{port}")
    if "interface" in processes:
        port = os.environ.get("INTERFACE_PORT", os.environ.get("PORT", "3030"))
        print(f"    Interface OLAP  : http://localhost:{port}")
    
    print(f"\n  Automatisation quotidienne :")
    print(f"    python daily_automation.py           # Exécution immédiate")
    print(f"    python daily_automation.py --schedule # Planification 24h")
    print(f"================================================================{C.END}")
    print(f"\n  Appuyez sur Ctrl+C pour arreter tous les composants.\n")

    # Gestion arret propre
    def shutdown(signum=None, frame=None):
        print(f"\n{C.YELLOW}[STOP] Arret des composants...{C.END}")
        for name, proc in processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  [{name}] arrete")
            except Exception:
                proc.kill()
                print(f"  [{name}] force kill")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Boucle principale : afficher les sorties
    try:
        while True:
            for name, proc in list(processes.items()):
                if proc.poll() is not None:
                    print(f"{C.RED}  [{name}] processus termine (code {proc.returncode}){C.END}")
                    del processes[name]
                    if not processes:
                        print(f"{C.RED}[ERREUR] Tous les processus se sont arretes.{C.END}")
                        sys.exit(1)
                else:
                    stream_output(proc, name)
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()

import csv
import os
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def run_step(step: str, script_path: str):
    print(f"[ETL] Running step: {step} -> {script_path}")
    
    # Use venv Python and pass environment variables
    venv_python = "olap/venv/Scripts/python.exe"
    env = os.environ.copy()
    result = subprocess.run([venv_python, script_path], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Step {step} failed: {result.stderr.strip()}")
    print(result.stdout.strip())


def append_log(run_id: str, started_at: datetime, ended_at: datetime, status: str, error_message: str = ""):
    log_path = Path("olap/reports/etl_run_log.csv")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            run_id,
            started_at.isoformat(),
            ended_at.isoformat(),
            status,
            "",
            "",
            "",
            error_message,
        ])


def main():
    load_dotenv("olap/configs/.env")
    run_id = os.getenv("ETL_RUN_ID") or datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
    os.environ["ETL_RUN_ID"] = run_id

    started_at = datetime.utcnow()
    steps = [
        ("extract", "olap/etl/extract/extract_oltp.py"),
        ("normalize", "olap/etl/transform/normalize.py"),
        ("deduplicate", "olap/etl/transform/deduplicate.py"),
        ("conform_dimensions", "olap/etl/transform/conform_dimensions.py"),
        ("load_dimensions", "olap/etl/load/load_dimensions.py"),
        ("load_facts", "olap/etl/load/load_facts.py"),
    ]

    try:
        for step_name, script in steps:
            run_step(step_name, script)

        ended_at = datetime.utcnow()
        append_log(run_id, started_at, ended_at, "SUCCESS", "")
        print(f"[ETL] Pipeline completed successfully. run_id={run_id}")
    except Exception as exc:
        ended_at = datetime.utcnow()
        append_log(run_id, started_at, ended_at, "FAILED", str(exc))
        raise


if __name__ == "__main__":
    main()

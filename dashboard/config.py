from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "backtests"
DASHBOARD_DIR = BASE_DIR / "dashboard"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
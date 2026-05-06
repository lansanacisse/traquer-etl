import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ORACLE_CONFIG = {
    "username": os.getenv("GLIMS_USER"),
    "password": os.getenv("GLIMS_PASSWORD"),
    "host": os.getenv("GLIMS_HOST", "vs-oracle-01t.chu-brest.fr"),
    "port": int(os.getenv("GLIMS_PORT", "1521")),
    "service_name": os.getenv("GLIMS_SERVICE", "GLIMST"),
}

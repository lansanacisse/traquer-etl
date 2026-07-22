import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / "output" / "local"


GLIMS_CONFIG = {
    "username": os.getenv("GLIMS_USER"),
    "password": os.getenv("GLIMS_PASSWORD"),
    "host": os.getenv("GLIMS_HOST"),
    "port": int(os.getenv("GLIMS_PORT", "1521")),
    "service_name": os.getenv("GLIMS_SERVICE"),
}


GAM_CONFIG = {
    "username": os.getenv("GAM_USER"),
    "password": os.getenv("GAM_PASSWORD"),
    "host": os.getenv("GAM_HOST"),
    "port": int(os.getenv("GAM_PORT", "1521")),
    "service_name": os.getenv("GAM_SERVICE"),
}

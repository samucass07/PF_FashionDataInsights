import os
import logging
from pathlib import Path

# ─────────────────────────────────────────────
# RUTAS DINÁMICAS DEL PROYECTO
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas de pipeline
DATA_DIR      = BASE_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR   = BASE_DIR / "reports"

# Rutas de consumo
APP_DIR       = BASE_DIR / "app"

# ─────────────────────────────────────────────
# CONFIGURACIÓN GLOBAL DE LOGS
# ─────────────────────────────────────────────
def setup_logging():
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s [%(levelname)s] %(message)s", 
        datefmt="%H:%M:%S"
    )
    return logging.getLogger(__name__)
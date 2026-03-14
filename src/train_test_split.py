import pandas as pd
import os
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
PROCESSED_PATH = "data/processed"
EVAL_WEEKS = 1 # Escondemos la última semana

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

def main():
    log.info("=" * 50)
    log.info("INICIANDO SPLIT TEMPORAL (TRAIN/TEST)")
    log.info("=" * 50)
    
    # 1. Cargar datos limpios del ETL
    # Usamos el sample del 10% que creaste en el paso anterior
    file_path = os.path.join(PROCESSED_PATH, "transactions_sample.csv")
    log.info(f"Cargando historial completo: {file_path}")
    df = pd.read_csv(file_path, parse_dates=['t_dat'])
    
    # 2. Definir fecha de corte
    max_date = df['t_dat'].max()
    cutoff_date = max_date - pd.Timedelta(weeks=EVAL_WEEKS)
    
    log.info(f"Fecha máxima en dataset: {max_date.date()}")
    log.info(f"Fecha de corte (Cutoff): {cutoff_date.date()}")
    
    # 3. Dividir el dataset
    train_df = df[df['t_dat'] <= cutoff_date]
    test_df = df[df['t_dat'] > cutoff_date]
    
    log.info("-" * 50)
    log.info(f"TRAIN (Para aprender): {len(train_df):,} transacciones")
    log.info(f"  Desde {train_df['t_dat'].min().date()} hasta {train_df['t_dat'].max().date()}")
    log.info(f"TEST  (Para evaluar):  {len(test_df):,} transacciones")
    log.info(f"  Desde {test_df['t_dat'].min().date()} hasta {test_df['t_dat'].max().date()}")
    log.info("-" * 50)
    
    # 4. Guardar los archivos bajo llave
    train_path = os.path.join(PROCESSED_PATH, "train_transactions.csv")
    test_path = os.path.join(PROCESSED_PATH, "test_transactions.csv")
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    log.info("Archivos guardados exitosamente. ¡Data Leakage solucionado!")

if __name__ == "__main__":
    main()
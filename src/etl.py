import pandas as pd
import numpy as np
import logging
from datetime import datetime
from config import RAW_DIR, PROCESSED_DIR, setup_logging

# --- CONFIGURACIÓN ---
# Las rutas base ahora vienen automáticamente de config.py
TRANSACTIONS_FILE = "transactions_train.csv"
ARTICLES_FILE     = "articles.csv"
CUSTOMERS_FILE    = "customers.csv"

SAMPLE_FRACTION   = 0.10   
CHUNK_SIZE        = 500_000 
RANDOM_SEED       = 42      

# Inicializamos el log estandarizado para Airflow
log = setup_logging()

# --- UTILIDADES ---
def ensure_dirs():
    # Usamos pathlib para crear la carpeta si no existe
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def log_stats(df, name):
    mem = df.memory_usage(deep=True).sum() / 1024**2
    log.info(f"{name}: {len(df):,} filas | Memoria: {mem:.2f} MB")

# --- PROCESAMIENTO ---

def process_customers():
    log.info("PASO 1: Procesando customers...")
    
    dtypes = {
        'customer_id': 'str',
        'FN': 'float32',
        'Active': 'float32',
        'club_member_status': 'category',
        'fashion_news_frequency': 'category'
    }
    
    # pathlib hace que unir rutas sea tan fácil como usar una barra "/"
    df = pd.read_csv(RAW_DIR / CUSTOMERS_FILE, dtype=dtypes)
    
    df["age"] = df["age"].fillna(df["age"].median()).astype(np.int16)
    
    for col in ["FN", "Active"]:
        df[col] = df[col].fillna(0).astype(np.int8)

    df_sample = df.sample(frac=SAMPLE_FRACTION, random_state=RANDOM_SEED).reset_index(drop=True)
    sampled_ids = set(df_sample["customer_id"])
    
    log_stats(df_sample, "Customers (Sample)")
    return df_sample, sampled_ids

def process_articles():
    log.info("PASO 2: Procesando articles...")
    
    df = pd.read_csv(RAW_DIR / ARTICLES_FILE, dtype={'article_id': str})
    df["article_id"] = df["article_id"].str.zfill(10)
    
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].fillna("unknown").str.strip().str.lower()
        if df[col].nunique() < 200:
            df[col] = df[col].astype('category')

    log_stats(df, "Articles")
    return df

def process_transactions(sampled_customer_ids):
    log.info("PASO 3: Procesando transacciones (Filtrado por Sample)...")
    
    filepath = RAW_DIR / TRANSACTIONS_FILE
    chunks_clean = []
    
    trans_dtypes = {
        "article_id": str,
        "customer_id": str,
        "price": "float32",
        "sales_channel_id": "int8"
    }

    reader = pd.read_csv(
        filepath,
        chunksize=CHUNK_SIZE,
        dtype=trans_dtypes,
        parse_dates=["t_dat"]
    )

    for i, chunk in enumerate(reader):
        chunk = chunk[chunk["customer_id"].isin(sampled_customer_ids)].copy()
        
        if not chunk.empty:
            chunk["article_id"] = chunk["article_id"].str.zfill(10)
            chunk = chunk[chunk["price"] > 0]
            chunks_clean.append(chunk)

        if i % 20 == 0 and i > 0:
            log.info(f"   Procesados {i * CHUNK_SIZE:,} registros de la fuente...")

    df_trans = pd.concat(chunks_clean, ignore_index=True)
    df_trans = df_trans.sort_values(["customer_id", "t_dat"])
    
    log_stats(df_trans, "Transactions (Final)")
    return df_trans

def ensure_consistency(df_trans, df_cust, df_art):
    log.info("PASO 4: Asegurando integridad referencial...")
    
    valid_art = set(df_art["article_id"])
    df_trans = df_trans[df_trans["article_id"].isin(valid_art)].copy()
    
    active_cust_ids = set(df_trans["customer_id"])
    df_cust = df_cust[df_cust["customer_id"].isin(active_cust_ids)].copy()
    
    active_art_ids = set(df_trans["article_id"])
    df_art = df_art[df_art["article_id"].isin(active_art_ids)].copy()

    return df_trans, df_cust, df_art

def save_all(df_trans, df_cust, df_art):
    log.info("PASO 5: Guardando resultados...")
    
    df_trans.to_csv(PROCESSED_DIR / "transactions_sample.csv", index=False)
    df_cust.to_csv(PROCESSED_DIR / "customers_clean.csv", index=False)
    df_art.to_csv(PROCESSED_DIR / "articles_clean.csv", index=False)
    
    log.info("¡Proceso completado exitosamente! ✓")

def run_etl():
    """Función principal orquestable por Airflow."""
    start = datetime.now()
    ensure_dirs()
    
    df_cust, sampled_ids = process_customers()
    df_art = process_articles()
    df_trans = process_transactions(sampled_ids)
    
    df_trans, df_cust, df_art = ensure_consistency(df_trans, df_cust, df_art)
    
    save_all(df_trans, df_cust, df_art)
    
    total_time = datetime.now() - start
    log.info(f"Tiempo total: {total_time.seconds // 60}m {total_time.seconds % 60}s")

if __name__ == "__main__":
    run_etl()
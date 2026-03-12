import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
RAW_DATA_PATH     = "./data/raw/"          
OUTPUT_PATH        = "./data/processed/"  

TRANSACTIONS_FILE = "transactions_train.csv"
ARTICLES_FILE     = "articles.csv"
CUSTOMERS_FILE    = "customers.csv"

SAMPLE_FRACTION   = 0.10   
CHUNK_SIZE        = 500_000 
RANDOM_SEED        = 42      

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# --- UTILIDADES ---
def ensure_dirs():
    os.makedirs(OUTPUT_PATH, exist_ok=True)

def log_stats(df, name):
    mem = df.memory_usage(deep=True).sum() / 1024**2
    log.info(f"{name}: {len(df):,} filas | Memoria: {mem:.2f} MB")

# --- PROCESAMIENTO ---

def process_customers():
    log.info("PASO 1: Procesando customers...")
    
    # Optimizamos tipos de datos al leer
    dtypes = {
        'customer_id': 'str',
        'FN': 'float32',
        'Active': 'float32',
        'club_member_status': 'category',
        'fashion_news_frequency': 'category'
    }
    
    df = pd.read_csv(os.path.join(RAW_DATA_PATH, CUSTOMERS_FILE), dtype=dtypes)
    
    # Imputación y limpieza
    df["age"] = df["age"].fillna(df["age"].median()).astype(np.int16)
    
    for col in ["FN", "Active"]:
        df[col] = df[col].fillna(0).astype(np.int8)

    # Sampling aleatorio
    df_sample = df.sample(frac=SAMPLE_FRACTION, random_state=RANDOM_SEED).reset_index(drop=True)
    sampled_ids = set(df_sample["customer_id"])
    
    log_stats(df_sample, "Customers (Sample)")
    return df_sample, sampled_ids

def process_articles():
    log.info("PASO 2: Procesando articles...")
    
    df = pd.read_csv(os.path.join(RAW_DATA_PATH, ARTICLES_FILE), dtype={'article_id': str})
    
    # El ID debe tener 10 dígitos SIEMPRE para cruzar con transacciones
    df["article_id"] = df["article_id"].str.zfill(10)
    
    # Limpieza de texto masiva
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].fillna("unknown").str.strip().str.lower()
        # Si la columna tiene baja cardinalidad, la pasamos a categoría
        if df[col].nunique() < 200:
            df[col] = df[col].astype('category')

    log_stats(df, "Articles")
    return df

def process_transactions(sampled_customer_ids):
    log.info("PASO 3: Procesando transacciones (Filtrado por Sample)...")
    
    filepath = os.path.join(RAW_DATA_PATH, TRANSACTIONS_FILE)
    chunks_clean = []
    
    # Definir tipos para ahorrar RAM durante la lectura de chunks
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
        # 1. Filtrar por el sample de clientes inmediatamente
        chunk = chunk[chunk["customer_id"].isin(sampled_customer_ids)].copy()
        
        if not chunk.empty:
            # 2. Estandarizar ID de artículo
            chunk["article_id"] = chunk["article_id"].str.zfill(10)
            
            # 3. Limpieza básica
            chunk = chunk[chunk["price"] > 0]
            chunks_clean.append(chunk)

        if i % 20 == 0 and i > 0:
            log.info(f"   Procesados {i * CHUNK_SIZE:,} registros de la fuente...")

    df_trans = pd.concat(chunks_clean, ignore_index=True)
    
    # Orden cronológico (esencial para sistemas de recomendación)
    df_trans = df_trans.sort_values(["customer_id", "t_dat"])
    
    log_stats(df_trans, "Transactions (Final)")
    return df_trans

def ensure_consistency(df_trans, df_cust, df_art):
    log.info("PASO 4: Asegurando integridad referencial...")
    
    # Solo nos quedamos con artículos que existen en el maestro
    valid_art = set(df_art["article_id"])
    df_trans = df_trans[df_trans["article_id"].isin(valid_art)].copy()
    
    # Solo nos quedamos con clientes que efectivamente compraron algo
    active_cust_ids = set(df_trans["customer_id"])
    df_cust = df_cust[df_cust["customer_id"].isin(active_cust_ids)].copy()
    
    # Solo artículos que fueron comprados por este sample
    active_art_ids = set(df_trans["article_id"])
    df_art = df_art[df_art["article_id"].isin(active_art_ids)].copy()

    return df_trans, df_cust, df_art

def save_all(df_trans, df_cust, df_art):
    log.info("PASO 5: Guardando resultados...")
    
    df_trans.to_csv(os.path.join(OUTPUT_PATH, "transactions_sample.csv"), index=False)
    df_cust.to_csv(os.path.join(OUTPUT_PATH, "customers_clean.csv"), index=False)
    df_art.to_csv(os.path.join(OUTPUT_PATH, "articles_clean.csv"), index=False)
    
    log.info("¡Proceso completado exitosamente! ✓")

def main():
    start = datetime.now()
    ensure_dirs()
    
    # Ejecución
    df_cust, sampled_ids = process_customers()
    df_art = process_articles()
    df_trans = process_transactions(sampled_ids)
    
    df_trans, df_cust, df_art = ensure_consistency(df_trans, df_cust, df_art)
    
    save_all(df_trans, df_cust, df_art)
    
    total_time = datetime.now() - start
    log.info(f"Tiempo total: {total_time.seconds // 60}m {total_time.seconds % 60}s")

if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime


RAW_DATA_PATH     = "./data/raw/"         
OUTPUT_PATH       = "./data/processed/" 

TRANSACTIONS_FILE = "transactions_train.csv"
ARTICLES_FILE     = "articles.csv"
CUSTOMERS_FILE    = "customers.csv"

SAMPLE_FRACTION   = 0.10   
CHUNK_SIZE        = 500_000 
RANDOM_SEED       = 42      

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

def ensure_dirs():
    """Crea los directorios de output si no existen."""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    log.info(f"Output dir: {OUTPUT_PATH}")


def log_shape(df, name):
    log.info(f"{name}: {df.shape[0]:,} filas x {df.shape[1]} columnas")


def log_nulls(df, name):
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        log.info(f"{name}: sin valores nulos ✓")
    else:
        log.warning(f"{name} - nulos por columna:\n{nulls.to_string()}")


def process_customers():
    
    log.info("PASO 1: Procesando customers...")

    df = pd.read_csv(os.path.join(RAW_DATA_PATH, CUSTOMERS_FILE))
    log_shape(df, "customers (raw)")
    log_nulls(df, "customers (raw)")

    # Eliminar duplicados por customer_id
    df = df.drop_duplicates(subset=["customer_id"])

    # Imputar edad faltante con la mediana
    median_age = df["age"].median()
    missing_age = df["age"].isnull().sum()
    df["age"] = df["age"].fillna(median_age)

    df["age"] = df["age"].astype(int)

    # Normalizar columnas de texto: strip y lowercase
    if "postal_code" in df.columns:
        df["postal_code"] = df["postal_code"].astype(str).str.strip()

    # FN_ACTIVE y newsletter: rellenar con 0 si falta (asumimos no activo)
    for col in ["FN", "Active", "club_member_status", "fashion_news_frequency"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")


    # ── Sampling ──────────────────────────────
    n_sample = int(len(df) * SAMPLE_FRACTION)
    sampled_ids = set(
        df["customer_id"].sample(n=n_sample, random_state=RANDOM_SEED).values
    )
    df_sample = df[df["customer_id"].isin(sampled_ids)].reset_index(drop=True)

    log.info(f"Sample: {len(sampled_ids):,} clientes ({SAMPLE_FRACTION*100:.0f}% del total)")

    return df_sample, sampled_ids

def process_articles():
    
    log.info("PASO 2: Procesando articles...")

    df = pd.read_csv(os.path.join(RAW_DATA_PATH, ARTICLES_FILE))
    log_shape(df, "articles (raw)")
    log_nulls(df, "articles (raw)")


    # Eliminar duplicados por article_id
    df = df.drop_duplicates(subset=["article_id"])

    # Rellenar descripciones faltantes con "Sin descripción"
    if "detail_desc" in df.columns:
        missing_desc = df["detail_desc"].isnull().sum()
        df["detail_desc"] = df["detail_desc"].fillna("Sin descripcion")

    # Normalizar columnas de texto categórico
    text_cols = [
        "prod_name", "product_type_name", "product_group_name",
        "graphical_appearance_name", "colour_group_name",
        "perceived_colour_value_name", "perceived_colour_master_name",
        "department_name", "index_name", "index_group_name",
        "section_name", "garment_group_name"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    # article_id como string con ceros a la izquierda
    df["article_id"] = df["article_id"].astype(str).str.zfill(10)

    return df


def process_transactions(sampled_customer_ids):

    log.info("PASO 3: Procesando transactions (chunks)...")

    filepath = os.path.join(RAW_DATA_PATH, TRANSACTIONS_FILE)
    chunks_clean = []
    total_raw = 0
    total_kept = 0
    chunk_num = 0

    reader = pd.read_csv(
        filepath,
        chunksize=CHUNK_SIZE,
        parse_dates=["t_dat"],
        dtype={"article_id": str, "customer_id": str}
    )

    for chunk in reader:
        chunk_num += 1
        total_raw += len(chunk)

        chunk = chunk[chunk["customer_id"].isin(sampled_customer_ids)]

        if chunk.empty:
            continue


        # Eliminar duplicados exactos (mismo cliente, artículo, fecha)
        chunk = chunk.drop_duplicates(subset=["t_dat", "customer_id", "article_id"])

        # article_id con ceros 
        chunk["article_id"] = chunk["article_id"].astype(str).str.zfill(10)

        # Eliminar precios negativos o nulos
        chunk = chunk[chunk["price"] > 0]
        chunk = chunk.dropna(subset=["price"])

        # sales_channel_id: solo valores válidos (1 = online, 2 = tienda)
        if "sales_channel_id" in chunk.columns:
            chunk = chunk[chunk["sales_channel_id"].isin([1, 2])]

        chunks_clean.append(chunk)
        total_kept += len(chunk)

        if chunk_num % 10 == 0:
            log.info(f"  Chunk {chunk_num} procesado... acumulado: {total_kept:,} transacciones")

    df_transactions = pd.concat(chunks_clean, ignore_index=True)

    # Ordenar por cliente y fecha
    df_transactions = df_transactions.sort_values(
        ["customer_id", "t_dat"]
    ).reset_index(drop=True)

    return df_transactions

def ensure_consistency(df_transactions, df_customers, df_articles):
    
    log.info("PASO 4: Verificando consistencia entre tablas...")

    valid_customers = set(df_customers["customer_id"])
    valid_articles  = set(df_articles["article_id"])

    df_transactions = df_transactions[
        df_transactions["customer_id"].isin(valid_customers) &
        df_transactions["article_id"].isin(valid_articles)
    ]

    # Filtrar customers y articles a los que realmente aparecen en transactions
    active_customers = set(df_transactions["customer_id"])
    active_articles  = set(df_transactions["article_id"])

    df_customers = df_customers[df_customers["customer_id"].isin(active_customers)].reset_index(drop=True)
    df_articles  = df_articles[df_articles["article_id"].isin(active_articles)].reset_index(drop=True)

    log.info(f"Clientes activos en el sample: {len(df_customers):,}")
    log.info(f"Artículos activos en el sample: {len(df_articles):,}")

    return df_transactions, df_customers, df_articles


def save_outputs(df_transactions, df_customers, df_articles):
   
    log.info("PASO 5: Guardando archivos procesados...")
   

    paths = {
        "transactions_sample.csv": df_transactions,
        "customers_clean.csv":     df_customers,
        "articles_clean.csv":      df_articles,
    }

    for filename, df in paths.items():
        out = os.path.join(OUTPUT_PATH, filename)
        df.to_csv(out, index=False)
        size_mb = os.path.getsize(out) / 1_000_000
        log.info(f"  Guardado: {filename} ({size_mb:.1f} MB, {len(df):,} filas)")


def main():
    start = datetime.now()
    log.info("Iniciando ETL - H&M Fashion Recommendations")
    log.info(f"Configuración: sample={SAMPLE_FRACTION*100:.0f}%, chunk_size={CHUNK_SIZE:,}, seed={RANDOM_SEED}")

    ensure_dirs()

    df_customers, sampled_ids = process_customers()
    df_articles               = process_articles()
    df_transactions           = process_transactions(sampled_ids)

    df_transactions, df_customers, df_articles = ensure_consistency(
        df_transactions, df_customers, df_articles
    )

    save_outputs(df_transactions, df_customers, df_articles)

    elapsed = datetime.now() - start
    log.info(f"ETL completado en {elapsed.seconds // 60}m {elapsed.seconds % 60}s ✓")


if __name__ == "__main__":
    main()


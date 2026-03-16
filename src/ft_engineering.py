import pandas as pd
import numpy as np
from config import PROCESSED_DIR, setup_logging

# Inicializamos el log estandarizado para Airflow
log = setup_logging()

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    log.info("Cargando datos limpios...")
    # Usamos pathlib de config.py, es mucho más limpio que os.path.join
    customers     = pd.read_csv(PROCESSED_DIR / "customers_clean.csv")
    articles      = pd.read_csv(PROCESSED_DIR / "articles_clean.csv")
    transactions  = pd.read_csv(PROCESSED_DIR / "train_transactions.csv", parse_dates=["t_dat"])
    
    log.info(f"  customers:    {len(customers):,} filas")
    log.info(f"  articles:     {len(articles):,} filas")
    log.info(f"  transactions: {len(transactions):,} filas")
    return customers, articles, transactions

# ─────────────────────────────────────────────
# FEATURE 1: SEGMENTO DE EDAD (GENERACIÓN)
# ─────────────────────────────────────────────

def add_age_segment(customers):
    log.info("Feature 1: Segmento de edad (generación)...")
    customers["age_group"] = pd.cut(
        customers["age"],
        bins=[0, 25, 40, 60, 120],
        labels=["Gen Z", "Millennials", "Gen X", "Seniors"]
    )
    dist = customers["age_group"].value_counts()
    log.info(f"  Distribución:\n{dist.to_string()}")
    return customers

# ─────────────────────────────────────────────
# FEATURE 2: FEATURES DE CLIENTE
# ─────────────────────────────────────────────

def build_customer_features(customers, transactions):
    log.info("Feature 2: Features de cliente (con ajuste de recencia)...")

    ref_date = transactions["t_dat"].max()

    agg = transactions.groupby("customer_id").agg(
        total_purchases   = ("article_id", "count"),
        unique_articles   = ("article_id", "nunique"),
        avg_price         = ("price", "mean"),
        last_purchase     = ("t_dat", "max"),
        first_purchase    = ("t_dat", "min"),
        preferred_channel = ("sales_channel_id", lambda x: x.mode()[0])
    ).reset_index()

    # Recencia en días
    agg["recency_days"] = (ref_date - agg["last_purchase"]).dt.days

    # Frecuencia: compras por semana activa
    agg["active_weeks"] = ((agg["last_purchase"] - agg["first_purchase"]).dt.days / 7).clip(lower=1)
    agg["purchase_frequency"] = agg["total_purchases"] / agg["active_weeks"]

    # Merge con customers
    features = customers.merge(agg, on="customer_id", how="left")

    # Rellenar métricas estándar con 0
    num_cols_zero = ["total_purchases", "unique_articles", "avg_price", "purchase_frequency"]
    for col in num_cols_zero:
        features[col] = features[col].fillna(0)
    
    # Rellenar recencia con 999 para diferenciar "nunca compró" de "compró hoy"
    features["recency_days"] = features["recency_days"].fillna(999)

    features["preferred_channel"] = features["preferred_channel"].fillna(1)

    # Limpiar columnas auxiliares
    features = features.drop(columns=["last_purchase", "first_purchase", "active_weeks"], errors="ignore")

    log.info(f"  Features de cliente generadas: {features.shape[1]} columnas")
    return features


# ─────────────────────────────────────────────
# FEATURE 3: POPULARIDAD POR GENERACIÓN
# ─────────────────────────────────────────────

def build_generation_popularity(customers, transactions):
    log.info("Feature 3: Popularidad por generación (ventana de 90 días)...")

    ref_date = transactions["t_dat"].max()
    cutoff_date = ref_date - pd.Timedelta(days=90)
    
    recent_transactions = transactions[transactions["t_dat"] >= cutoff_date].copy()
    log.info(f"   Filtradas {len(recent_transactions):,} transacciones recientes.")

    tx_with_gen = recent_transactions.merge(
        customers[["customer_id", "age_group"]], on="customer_id", how="left"
    )

    gen_popularity = (
        tx_with_gen.groupby(["age_group", "article_id"], observed=False)
        .size()
        .reset_index(name="purchase_count")
        .sort_values(["age_group", "purchase_count"], ascending=[True, False])
    )

    gen_popularity["rank_in_generation"] = gen_popularity.groupby("age_group", observed=False)["purchase_count"].rank(
        ascending=False, method="first"
    ).astype(int)

    for gen in gen_popularity["age_group"].unique():
        if pd.notna(gen):
            top3 = gen_popularity[gen_popularity["age_group"] == gen].head(3)["article_id"].tolist()
            log.info(f"  {gen} — Top 3: {top3}")

    return gen_popularity

# ─────────────────────────────────────────────
# FEATURE 4: FEATURES DE ARTÍCULO 
# ─────────────────────────────────────────────

def build_article_features(articles, transactions):
    log.info("Feature 4: Features de artículo (ventana de 90 días)...")

    ref_date = transactions["t_dat"].max()
    cutoff_date = ref_date - pd.Timedelta(days=90)
    recent_transactions = transactions[transactions["t_dat"] >= cutoff_date].copy()

    agg = recent_transactions.groupby("article_id").agg(
        global_popularity = ("customer_id", "count"),
        unique_buyers     = ("customer_id", "nunique"),
        avg_price_sold    = ("price", "mean"),
    ).reset_index()

    agg["global_rank"] = agg["global_popularity"].rank(ascending=False, method="first").astype(int)

    features = articles.merge(agg, on="article_id", how="left")
    
    features["global_popularity"] = features["global_popularity"].fillna(0)
    features["unique_buyers"]     = features["unique_buyers"].fillna(0)
    
    max_rank = features["global_rank"].max()
    features["global_rank"] = features["global_rank"].fillna(max_rank + 1 if pd.notna(max_rank) else 1)

    log.info(f"  Features de artículo generadas: {features.shape[1]} columnas")
    return features

# ─────────────────────────────────────────────
# FEATURE 5: MATRIZ DE INTERACCIONES
# ─────────────────────────────────────────────

def build_interaction_matrix(transactions, min_purchases=2):
    log.info(f"Feature 5: Matriz de interacciones (mínimo {min_purchases} compras por cliente)...")

    user_counts = transactions.groupby("customer_id").size()
    
    active_users = user_counts[user_counts >= min_purchases].index
    filtered_tx = transactions[transactions["customer_id"].isin(active_users)]
    
    log.info(f"   Usuarios filtrados: {len(active_users):,} de {len(user_counts):,}")

    interactions = (
        filtered_tx.groupby(["customer_id", "article_id"])
        .size()
        .reset_index(name="interaction_count")
    )

    n_users = interactions['customer_id'].nunique()
    n_items = interactions['article_id'].nunique()
    density = len(interactions) / (n_users * n_items) * 100 if n_users > 0 else 0
    
    log.info(f"  Pares cliente-artículo: {len(interactions):,}")
    log.info(f"  Densidad final: {density:.4f}%")
    
    return interactions

# ─────────────────────────────────────────────
# MAIN REFACTOREADO (E2E)
# ─────────────────────────────────────────────

def run_feature_engineering():
    """Función principal orquestable por Airflow."""
    log.info("=" * 50)
    log.info("INICIANDO PIPELINE DE FEATURE ENGINEERING E2E")
    log.info("=" * 50)

    customers, articles, transactions = load_data()

    customers = add_age_segment(customers)
    feat_customers = build_customer_features(customers, transactions)
    gen_popularity = build_generation_popularity(customers, transactions)
    feat_articles = build_article_features(articles, transactions)
    interactions = build_interaction_matrix(transactions, min_purchases=2)

    outputs = {
        "features_customers.csv":    feat_customers,
        "features_articles.csv":     feat_articles,
        "gen_popularity.csv":        gen_popularity,
        "features_interactions.csv": interactions,
    }

    log.info("Guardando archivos procesados...")
    for filename, df in outputs.items():
        # Usamos pathlib para guardar
        path = PROCESSED_DIR / filename
        df.to_csv(path, index=False)
        log.info(f"  Generado: {path} ({len(df):,} filas)")

    log.info("=" * 50)
    log.info("PIPELINE COMPLETADO CON ÉXITO ✓")
    log.info("=" * 50)

if __name__ == "__main__":
    run_feature_engineering()
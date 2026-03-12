import pandas as pd
import numpy as np
import os
import logging

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

PROCESSED_PATH = "./Data/processed/"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    log.info("Cargando datos limpios...")
    customers     = pd.read_csv(os.path.join(PROCESSED_PATH, "customers_clean.csv"))
    articles      = pd.read_csv(os.path.join(PROCESSED_PATH, "articles_clean.csv"))
    transactions  = pd.read_csv(os.path.join(PROCESSED_PATH, "transactions_sample.csv"), parse_dates=["t_dat"])
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

    log.info("Feature 2: Features de cliente...")

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

    # Rellenar clientes sin transacciones (cold start)
    num_cols = ["total_purchases", "unique_articles", "avg_price", "recency_days", "purchase_frequency"]
    for col in num_cols:
        features[col] = features[col].fillna(0)
    features["preferred_channel"] = features["preferred_channel"].fillna(1)

    # Limpiar columnas auxiliares
    features = features.drop(columns=["last_purchase", "first_purchase", "active_weeks"], errors="ignore")

    log.info(f"  Features de cliente generadas: {features.shape[1]} columnas")
    return features

# ─────────────────────────────────────────────
# FEATURE 3: POPULARIDAD POR GENERACIÓN
# ─────────────────────────────────────────────

def build_generation_popularity(customers, transactions):
    log.info("Feature 3: Popularidad por generación...")

    # Unir transacciones con segmento de edad
    tx_with_gen = transactions.merge(
        customers[["customer_id", "age_group"]], on="customer_id", how="left"
    )

    # Ranking por generación
    gen_popularity = (
        tx_with_gen.groupby(["age_group", "article_id"])
        .size()
        .reset_index(name="purchase_count")
        .sort_values(["age_group", "purchase_count"], ascending=[True, False])
    )

    # Rank dentro de cada generación
    gen_popularity["rank_in_generation"] = gen_popularity.groupby("age_group")["purchase_count"].rank(
        ascending=False, method="first"
    ).astype(int)

    for gen in gen_popularity["age_group"].unique():
        top3 = gen_popularity[gen_popularity["age_group"] == gen].head(3)["article_id"].tolist()
        log.info(f"  {gen} — Top 3: {top3}")

    return gen_popularity

# ─────────────────────────────────────────────
# FEATURE 4: FEATURES DE ARTÍCULO
# ─────────────────────────────────────────────

def build_article_features(articles, transactions):
    log.info("Feature 4: Features de artículo...")

    agg = transactions.groupby("article_id").agg(
        global_popularity = ("customer_id", "count"),
        unique_buyers     = ("customer_id", "nunique"),
        avg_price_sold    = ("price", "mean"),
    ).reset_index()

    agg["global_rank"] = agg["global_popularity"].rank(ascending=False, method="first").astype(int)

    features = articles.merge(agg, on="article_id", how="left")
    features["global_popularity"] = features["global_popularity"].fillna(0)
    features["unique_buyers"]     = features["unique_buyers"].fillna(0)
    features["global_rank"]       = features["global_rank"].fillna(features["global_rank"].max() + 1)

    log.info(f"  Features de artículo generadas: {features.shape[1]} columnas")
    return features

# ─────────────────────────────────────────────
# FEATURE 5: MATRIZ DE INTERACCIONES
# ─────────────────────────────────────────────

def build_interaction_matrix(transactions):

    log.info("Feature 5: Matriz de interacciones cliente-artículo...")

    interactions = (
        transactions.groupby(["customer_id", "article_id"])
        .size()
        .reset_index(name="interaction_count")
    )

    log.info(f"  Pares cliente-artículo: {len(interactions):,}")
    log.info(f"  Densidad: {len(interactions) / (interactions['customer_id'].nunique() * interactions['article_id'].nunique()) * 100:.4f}%")
    return interactions

# ─────────────────────────────────────────────
# GUARDAR OUTPUTS
# ─────────────────────────────────────────────

def save_features(features_customers, features_articles, gen_popularity, interactions):
    log.info("Guardando features...")

    outputs = {
        "features_customers.csv":    features_customers,
        "features_articles.csv":     features_articles,
        "gen_popularity.csv":        gen_popularity,
        "features_interactions.csv": interactions,
    }

    for filename, df in outputs.items():
        path = os.path.join(PROCESSED_PATH, filename)
        df.to_csv(path, index=False)
        size_mb = os.path.getsize(path) / 1_000_000
        log.info(f"  Guardado: {filename} ({size_mb:.1f} MB, {len(df):,} filas)")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    log.info("=" * 50)
    log.info("INICIANDO PIPELINE DE FEATURE ENGINEERING")
    log.info("=" * 50)

    customers, articles, transactions = load_data()

    customers        = add_age_segment(customers)
    feat_customers   = build_customer_features(customers, transactions)
    gen_popularity   = build_generation_popularity(customers, transactions)
    feat_articles    = build_article_features(articles, transactions)
    interactions     = build_interaction_matrix(transactions)

    save_features(feat_customers, feat_articles, gen_popularity, interactions)

    log.info("=" * 50)
    log.info("PIPELINE COMPLETADO ✓")
    log.info("Archivos generados en data/processed/:")
    log.info("  features_customers.csv  — features por cliente")
    log.info("  features_articles.csv   — features por artículo")
    log.info("  gen_popularity.csv      — ranking por generación")
    log.info("  features_interactions.csv — matriz cliente-artículo")
    log.info("=" * 50)

if __name__ == "__main__":
    main()
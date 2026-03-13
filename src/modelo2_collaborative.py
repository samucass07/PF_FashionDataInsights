
"""
USO: python modelo2_collaborative_filtering.py
REQUISITOS: pip install scikit-learn scipy
"""

import pandas as pd
import numpy as np
import os
import logging
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

PROCESSED_PATH = "data/processed"
TOP_K          = 12
N_NEIGHBORS    = 20
EVAL_WEEKS     = 1
BATCH_SIZE     = 500   # clientes por batch — ajusta según tu RAM
                       # 500 es seguro para 8GB, puedes subir a 1000 con 16GB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    log.info("Cargando datos...")
    transactions = pd.read_csv(
        os.path.join(PROCESSED_PATH, "transactions_sample.csv"),
        parse_dates=["t_dat"]
    )
    interactions = pd.read_csv(os.path.join(PROCESSED_PATH, "features_interactions.csv"))

    log.info(f"  transactions: {len(transactions):,} filas")
    log.info(f"  interactions: {len(interactions):,} pares cliente-artículo")
    log.info(f"  Clientes en matriz: {interactions['customer_id'].nunique():,}")
    log.info(f"  Artículos en matriz: {interactions['article_id'].nunique():,}")
    return transactions, interactions

# ─────────────────────────────────────────────
# SPLIT TEMPORAL
# ─────────────────────────────────────────────

def temporal_split(transactions, eval_weeks=1):
    cutoff = transactions["t_dat"].max() - pd.Timedelta(weeks=eval_weeks)
    train  = transactions[transactions["t_dat"] <= cutoff]
    test   = transactions[transactions["t_dat"] >  cutoff]
    log.info(f"Cutoff: {cutoff.date()}")
    log.info(f"Train: {len(train):,} ({train['t_dat'].min().date()} → {train['t_dat'].max().date()})")
    log.info(f"Test:  {len(test):,}  ({test['t_dat'].min().date()} → {test['t_dat'].max().date()})")
    log.info(f"Clientes en test: {test['customer_id'].nunique():,}")
    return train, test

# ─────────────────────────────────────────────
# CONSTRUCCIÓN DE MATRIZ SPARSE
# ─────────────────────────────────────────────

def build_user_item_matrix(interactions):
    log.info("Construyendo matriz usuario-artículo sparse...")

    customers_unique = interactions["customer_id"].unique()
    articles_unique  = interactions["article_id"].unique()

    customer_idx = {c: i for i, c in enumerate(customers_unique)}
    article_idx  = {a: i for i, a in enumerate(articles_unique)}

    rows = interactions["customer_id"].map(customer_idx)
    cols = interactions["article_id"].map(article_idx)
    data = interactions["interaction_count"].values

    matrix = csr_matrix(
        (data, (rows, cols)),
        shape=(len(customer_idx), len(article_idx))
    )

    density = matrix.nnz / (matrix.shape[0] * matrix.shape[1]) * 100
    log.info(f"  Shape: {matrix.shape[0]:,} clientes x {matrix.shape[1]:,} artículos")
    log.info(f"  Interacciones no nulas: {matrix.nnz:,}")
    log.info(f"  Densidad: {density:.4f}%")

    return matrix, customer_idx, article_idx

# ─────────────────────────────────────────────
# PREDICCIÓN POR BATCHES (sin materializar matriz completa)
# ─────────────────────────────────────────────

def predict_batches(matrix, customer_idx, article_idx, top_k=12, n_neighbors=20, batch_size=500):
    """
    Genera recomendaciones procesando la similitud por batches.

    En lugar de calcular toda la matriz de similitud (135k x 135k = 137GB),
    calcula la similitud solo para un batch de clientes a la vez contra
    todos los demás. Cada batch ocupa ~550MB en RAM.

    Batch de 500 clientes:
      500 x 135,738 x 8 bytes = ~543 MB — manejable con 8GB RAM
    """
    log.info(f"Generando recomendaciones por batches (batch_size={batch_size})...")

    idx_to_customer = {v: k for k, v in customer_idx.items()}
    idx_to_article  = {v: k for k, v in article_idx.items()}

    n_customers   = matrix.shape[0]
    recommendations = []
    n_batches     = (n_customers + batch_size - 1) // batch_size

    for batch_num, start in enumerate(range(0, n_customers, batch_size)):
        end         = min(start + batch_size, n_customers)
        batch_matrix = matrix[start:end]  # submatriz del batch actual

        # Similitud solo del batch contra todos los clientes
        # Shape: (batch_size, n_customers) — manejable en RAM
        sim_batch = cosine_similarity(batch_matrix, matrix, dense_output=True)

        for local_i in range(end - start):
            global_i    = start + local_i
            customer_id = idx_to_customer[global_i]

            sim_scores  = sim_batch[local_i].copy()
            sim_scores[global_i] = 0  # excluir a sí mismo

            # Top N vecinos
            neighbor_indices = np.argsort(sim_scores)[::-1][:n_neighbors]
            neighbor_weights = sim_scores[neighbor_indices]

            # Scores ponderados de artículos de los vecinos
            neighbor_matrix = matrix[neighbor_indices].toarray()
            item_scores     = neighbor_weights @ neighbor_matrix

            # Excluir artículos ya comprados
            already_bought = set(matrix[global_i].nonzero()[1])

            ranked    = np.argsort(item_scores)[::-1]
            top_items = [
                idx_to_article[j]
                for j in ranked
                if j not in already_bought
            ][:top_k]

            recommendations.append({
                "customer_id": customer_id,
                "predictions": top_items
            })

        if (batch_num + 1) % 10 == 0 or batch_num == 0:
            log.info(f"  Batch {batch_num+1}/{n_batches} — {end:,}/{n_customers:,} clientes procesados")

    log.info(f"  Recomendaciones generadas: {len(recommendations):,} clientes")
    return pd.DataFrame(recommendations)

# ─────────────────────────────────────────────
# EVALUACIÓN: MAP@K
# ─────────────────────────────────────────────

def average_precision_at_k(predicted, actual, k=12):
    if not actual:
        return 0.0
    predicted = predicted[:k]
    hits, score = 0, 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            hits += 1
            score += hits / (i + 1)
    return score / min(len(actual), k)

def evaluate(recommendations, test):
    log.info("Evaluando Modelo 2...")

    ground_truth = (
        test.groupby("customer_id")["article_id"]
        .apply(list)
        .to_dict()
    )

    rec_dict          = dict(zip(recommendations["customer_id"], recommendations["predictions"]))
    ap_scores         = []
    clientes_sin_pred = 0

    for customer_id, actual in ground_truth.items():
        predicted = rec_dict.get(customer_id, [])
        if not predicted:
            clientes_sin_pred += 1
        ap = average_precision_at_k(predicted, actual, k=TOP_K)
        ap_scores.append(ap)

    map_score = np.mean(ap_scores)
    coverage  = len([s for s in ap_scores if s > 0]) / len(ap_scores) * 100

    log.info(f"  MAP@{TOP_K}:            {map_score:.4f}")
    log.info(f"  Cobertura:          {coverage:.1f}% clientes con al menos 1 hit")
    log.info(f"  Clientes evaluados: {len(ap_scores):,}")
    log.info(f"  Sin predicción:     {clientes_sin_pred:,} (cold start)")

    return {
        "model":        "User-Based Collaborative Filtering",
        "map_at_12":    map_score,
        "coverage_pct": coverage,
        "n_evaluated":  len(ap_scores),
        "cold_start":   clientes_sin_pred
    }

# ─────────────────────────────────────────────
# GUARDAR RESULTADOS
# ─────────────────────────────────────────────

def save_results(recommendations, metrics):
    recs_exploded = (
        recommendations.explode("predictions")
        .rename(columns={"predictions": "article_id"})
    )
    recs_exploded["rank"] = recs_exploded.groupby("customer_id").cumcount() + 1

    path_r = os.path.join(PROCESSED_PATH, "recommendations_model2.csv")
    recs_exploded.to_csv(path_r, index=False)
    log.info(f"Recomendaciones guardadas: {path_r}")

    path_m = os.path.join(PROCESSED_PATH, "metrics_model2.csv")
    pd.DataFrame([metrics]).to_csv(path_m, index=False)
    log.info(f"Métricas guardadas: {path_m}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    log.info("=" * 55)
    log.info("MODELO 2 — User-Based Collaborative Filtering")
    log.info("=" * 55)

    transactions, interactions = load_data()
    train, test                = temporal_split(transactions, EVAL_WEEKS)

    # Filtrar interactions para usar solo clientes en train
    train_customer_ids = set(train["customer_id"].unique())
    interactions_train = interactions[interactions["customer_id"].isin(train_customer_ids)]
    log.info(f"Interacciones en train: {len(interactions_train):,}")

    matrix, customer_idx, article_idx = build_user_item_matrix(interactions_train)

    recommendations = predict_batches(
        matrix, customer_idx, article_idx,
        top_k=TOP_K, n_neighbors=N_NEIGHBORS, batch_size=BATCH_SIZE
    )

    metrics = evaluate(recommendations, test)
    save_results(recommendations, metrics)

    log.info("=" * 55)
    log.info(f"RESULTADO FINAL  →  MAP@12: {metrics['map_at_12']:.4f}")
    log.info(f"Cold Start:          {metrics['cold_start']:,} clientes sin predicción")
    log.info("=" * 55)

if __name__ == "__main__":
    main()
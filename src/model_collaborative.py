import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from config import PROCESSED_DIR, setup_logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PRODUCCIÓN
# ─────────────────────────────────────────────
# En producción ya no iteramos, usamos el hiperparámetro óptimo 
# descubierto en la fase de investigación (Grid Search).
N_NEIGHBORS_OPTIMAL = 200
TOP_K          = 12
BATCH_SIZE     = 200   

# Inicializamos el log estandarizado para Airflow
log = setup_logging()

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    log.info("Cargando datos limpios y divididos...")
    dtypes = {'customer_id': str, 'article_id': str}
    
    # Usamos pathlib para acceder a las rutas
    train = pd.read_csv(PROCESSED_DIR / "train_transactions.csv", dtype=dtypes, parse_dates=["t_dat"])
    test = pd.read_csv(PROCESSED_DIR / "test_transactions.csv", dtype=dtypes, parse_dates=["t_dat"])
    interactions = pd.read_csv(PROCESSED_DIR / "features_interactions.csv", dtype=dtypes)

    log.info(f"  OK: Train ({len(train):,}), Test ({len(test):,}), Interactions ({len(interactions):,})")
    return train, test, interactions

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

    matrix = csr_matrix((data, (rows, cols)), shape=(len(customer_idx), len(article_idx)))

    density = matrix.nnz / (matrix.shape[0] * matrix.shape[1]) * 100
    log.info(f"  Shape: {matrix.shape[0]:,} clientes x {matrix.shape[1]:,} artículos | Densidad: {density:.4f}%")

    return matrix, customer_idx, article_idx

# ─────────────────────────────────────────────
# PREDICCIÓN
# ─────────────────────────────────────────────

def predict_for_test_users(matrix, customer_idx, article_idx, test_customer_ids, top_k=12, n_neighbors=200, batch_size=200):
    idx_to_article = {v: k for k, v in article_idx.items()}
    idx_to_customer = {v: k for k, v in customer_idx.items()}

    test_indices = [customer_idx[c] for c in test_customer_ids if c in customer_idx]
    n_test    = len(test_indices)
    n_batches = (n_test + batch_size - 1) // batch_size
    
    recommendations = []

    for batch_num, start in enumerate(range(0, n_test, batch_size)):
        end          = min(start + batch_size, n_test)
        batch_global = test_indices[start:end]
        batch_matrix = matrix[batch_global]

        sim_batch = cosine_similarity(batch_matrix, matrix, dense_output=True)

        for local_i, global_i in enumerate(batch_global):
            customer_id = idx_to_customer[global_i]

            sim_scores           = sim_batch[local_i].copy()
            sim_scores[global_i] = 0  

            neighbor_indices = np.argsort(sim_scores)[::-1][:n_neighbors]
            neighbor_weights = sim_scores[neighbor_indices]

            neighbor_matrix = matrix[neighbor_indices].toarray()
            item_scores     = neighbor_weights @ neighbor_matrix

            already_bought = set(matrix[global_i].nonzero()[1])

            non_zero_items = (item_scores > 0).sum()
            ranked         = np.argsort(item_scores)[::-1][:non_zero_items]
            
            top_items = [idx_to_article[j] for j in ranked if j not in already_bought][:top_k]

            recommendations.append({"customer_id": customer_id, "predictions": top_items})

    return pd.DataFrame(recommendations)

# ─────────────────────────────────────────────
# EVALUACIÓN
# ─────────────────────────────────────────────

def average_precision_at_k(predicted, actual, k=12):
    if not actual: return 0.0
    predicted = predicted[:k]
    hits, score = 0, 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            hits += 1
            score += hits / (i + 1)
    return score / min(len(actual), k)

def evaluate(recommendations, test):
    ground_truth = test.groupby("customer_id")["article_id"].apply(list).to_dict()
    rec_dict          = dict(zip(recommendations["customer_id"], recommendations["predictions"]))
    ap_scores         = []
    clientes_sin_pred = 0

    for customer_id, actual in ground_truth.items():
        predicted = rec_dict.get(customer_id, [])
        if not predicted: clientes_sin_pred += 1
        ap_scores.append(average_precision_at_k(predicted, actual, k=TOP_K))

    map_score = np.mean(ap_scores)
    coverage  = len([s for s in ap_scores if s > 0]) / len(ap_scores) * 100

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
    recs_exploded = recommendations.explode("predictions").rename(columns={"predictions": "article_id"})
    recs_exploded["rank"] = recs_exploded.groupby("customer_id").cumcount() + 1

    path_r = PROCESSED_DIR / "recommendations_model2.csv"
    recs_exploded.to_csv(path_r, index=False)
    
    path_m = PROCESSED_DIR / "metrics_model2.csv"
    pd.DataFrame([metrics]).to_csv(path_m, index=False)
    log.info(f"Resultados guardados en disco.")

# ─────────────────────────────────────────────
# MAIN REFACTOREADO PARA MLOPS
# ─────────────────────────────────────────────

def run_collaborative_model():
    """Función principal orquestable por Airflow."""
    log.info("=" * 60)
    log.info(f"MODELO 2 — FILTRADO COLABORATIVO (PRODUCCIÓN - K={N_NEIGHBORS_OPTIMAL})")
    log.info("=" * 60)

    train, test, interactions = load_data()
    matrix, customer_idx, article_idx = build_user_item_matrix(interactions)
    test_customer_ids = list(test["customer_id"].unique())

    log.info(f"▶ Generando predicciones usando {N_NEIGHBORS_OPTIMAL} vecinos...")
    
    recs = predict_for_test_users(
        matrix, customer_idx, article_idx,
        test_customer_ids=test_customer_ids,
        top_k=TOP_K, n_neighbors=N_NEIGHBORS_OPTIMAL, batch_size=BATCH_SIZE
    )
    
    metrics = evaluate(recs, test)
    
    log.info("=" * 60)
    log.info(f"RESULTADOS: MAP@12: {metrics['map_at_12']:.5f} | Cobertura: {metrics['coverage_pct']:.1f}%")
    log.info("=" * 60)
    
    save_results(recs, metrics)
    log.info("¡Modelo Colaborativo ejecutado con éxito!")

if __name__ == "__main__":
    run_collaborative_model()
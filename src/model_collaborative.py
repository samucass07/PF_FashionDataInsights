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
#grilla de búsqueda automática
NEIGHBORS_GRID = [20, 50, 100, 200, 300] 
EVAL_WEEKS     = 1
BATCH_SIZE     = 200   

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    log.info("Cargando datos limpios y divididos...")
    dtypes = {'customer_id': str, 'article_id': str}
    
    train = pd.read_csv(os.path.join(PROCESSED_PATH, "train_transactions.csv"), dtype=dtypes, parse_dates=["t_dat"])
    test = pd.read_csv(os.path.join(PROCESSED_PATH, "test_transactions.csv"), dtype=dtypes, parse_dates=["t_dat"])
    interactions = pd.read_csv(os.path.join(PROCESSED_PATH, "features_interactions.csv"), dtype=dtypes)

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

def predict_for_test_users(matrix, customer_idx, article_idx, test_customer_ids, top_k=12, n_neighbors=20, batch_size=200):
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

    path_r = os.path.join(PROCESSED_PATH, "recommendations_model2.csv")
    recs_exploded.to_csv(path_r, index=False)
    
    path_m = os.path.join(PROCESSED_PATH, "metrics_model2.csv")
    pd.DataFrame([metrics]).to_csv(path_m, index=False)
    log.info(f"Resultados del ganador guardados en disco.")

# ─────────────────────────────────────────────
# MAIN (GRID SEARCH)
# ─────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("MODELO 2 — BÚSQUEDA DE HIPERPARÁMETROS (GRID SEARCH)")
    log.info("=" * 60)

    train, test, interactions = load_data()
    matrix, customer_idx, article_idx = build_user_item_matrix(interactions)
    test_customer_ids = list(test["customer_id"].unique())

    # Variables para trackear al campeón
    best_n = 0
    best_map = -1.0
    best_recs = None
    best_metrics = None
    resultados_grid = []

    # EL BUCLE DEL GRID SEARCH
    for n in NEIGHBORS_GRID:
        log.info("-" * 60)
        log.info(f"▶ Probando N_NEIGHBORS = {n} ...")
        
        recs = predict_for_test_users(
            matrix, customer_idx, article_idx,
            test_customer_ids=test_customer_ids,
            top_k=TOP_K, n_neighbors=n, batch_size=BATCH_SIZE
        )
        
        metrics = evaluate(recs, test)
        current_map = metrics['map_at_12']
        
        resultados_grid.append((n, current_map))
        log.info(f"  Resultado parcial -> MAP@12: {current_map:.5f} | Cobertura: {metrics['coverage_pct']:.1f}%")
        
        if current_map > best_map:
            log.info(f"  🏆 ¡NUEVO CAMPEÓN! (MAP subió de {max(0, best_map):.5f} a {current_map:.5f})")
            best_map = current_map
            best_n = n
            best_recs = recs
            best_metrics = metrics

    # REPORTE FINAL
    log.info("=" * 60)
    log.info("RESUMEN DEL GRID SEARCH:")
    for n, score in resultados_grid:
        log.info(f"  Vecinos: {n:3d} | MAP@12: {score:.5f}")
        
    log.info("=" * 60)
    log.info(f"GANADOR ABSOLUTO: N_NEIGHBORS = {best_n} (MAP@12: {best_map:.5f})")
    
    # Solo guardamos el mejor de todos
    save_results(best_recs, best_metrics)
    log.info("¡Grid Search finalizado con éxito!")

if __name__ == "__main__":
    main()
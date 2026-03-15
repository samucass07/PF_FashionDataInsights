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
BATCH_SIZE     = 200   # batches de clientes en test

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def load_data():
    """
    Carga los archivos pre-divididos. 
    Al usar dtypes aquí, ahorramos memoria y evitamos casteos manuales después.
    """
    log.info("Cargando datos limpios y divididos...")
    
    dtypes = {'customer_id': str, 'article_id': str}
    
    # 1. El pasado (lo que el modelo usará para aprender)
    train = pd.read_csv(
        os.path.join(PROCESSED_PATH, "train_transactions.csv"),
        dtype=dtypes, 
        parse_dates=["t_dat"]
    )
    
    # 2. El futuro (el examen para evaluar el modelo)
    test = pd.read_csv(
        os.path.join(PROCESSED_PATH, "test_transactions.csv"),
        dtype=dtypes, 
        parse_dates=["t_dat"]
    )
    
    # 3. Las interacciones (ya filtradas para usar solo datos de train)
    interactions = pd.read_csv(
        os.path.join(PROCESSED_PATH, "features_interactions.csv"),
        dtype=dtypes
    )

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

    matrix = csr_matrix(
        (data, (rows, cols)),
        shape=(len(customer_idx), len(article_idx))
    )

    density = matrix.nnz / (matrix.shape[0] * matrix.shape[1]) * 100
    log.info(f"  Shape: {matrix.shape[0]:,} clientes x {matrix.shape[1]:,} artículos")
    log.info(f"  Densidad: {density:.4f}%")

    return matrix, customer_idx, article_idx

# ─────────────────────────────────────────────
# PREDICCIÓN SOLO PARA CLIENTES EN TEST
# ─────────────────────────────────────────────

def predict_for_test_users(matrix, customer_idx, article_idx, test_customer_ids,
                            top_k=12, n_neighbors=20, batch_size=200):
    """
    Solo genera recomendaciones para los clientes presentes en test.
    Justificación: no tiene sentido calcular similitud para los 135k
    clientes si la evaluación solo cubre 7k. Esto reduce el tiempo
    de ~2.5 horas a ~5 minutos.
    """
    idx_to_article = {v: k for k, v in article_idx.items()}
    
    # 1. OPTIMIZACIÓN DE VELOCIDAD: Diccionario inverso de clientes fuera del loop
    # Esto elimina la complejidad O(N) que hacía que el código tardara horas.
    idx_to_customer = {v: k for k, v in customer_idx.items()}

    # Índices en la matriz de los clientes que están en test
    test_indices = [
        customer_idx[c]
        for c in test_customer_ids
        if c in customer_idx
    ]

    n_test    = len(test_indices)
    n_batches = (n_test + batch_size - 1) // batch_size
    log.info(f"Generando recomendaciones para {n_test:,} clientes en test (batch_size={batch_size})...")
    log.info(f"  Clientes en test sin historial (cold start): {len(test_customer_ids) - n_test:,}")

    recommendations = []

    for batch_num, start in enumerate(range(0, n_test, batch_size)):
        end          = min(start + batch_size, n_test)
        batch_global = test_indices[start:end]
        batch_matrix = matrix[batch_global]

        # Similitud del batch de test contra TODOS los clientes
        # Shape: (batch_size, 135k) — ~218MB para batch=200, manejable
        sim_batch = cosine_similarity(batch_matrix, matrix, dense_output=True)

        for local_i, global_i in enumerate(batch_global):
            
            # USAMOS EL DICCIONARIO INVERSO: Acceso instantáneo O(1)
            customer_id = idx_to_customer[global_i]

            sim_scores           = sim_batch[local_i].copy()
            sim_scores[global_i] = 0  # excluir a sí mismo

            neighbor_indices = np.argsort(sim_scores)[::-1][:n_neighbors]
            neighbor_weights = sim_scores[neighbor_indices]

            neighbor_matrix = matrix[neighbor_indices].toarray()
            item_scores     = neighbor_weights @ neighbor_matrix

            already_bought = set(matrix[global_i].nonzero()[1])

            # 2. OPTIMIZACIÓN LÓGICA: Filtrar scores en cero para no recomendar basura
            non_zero_items = (item_scores > 0).sum()
            ranked         = np.argsort(item_scores)[::-1][:non_zero_items]
            
            top_items = [
                idx_to_article[j]
                for j in ranked
                if j not in already_bought
            ][:top_k]

            recommendations.append({
                "customer_id": customer_id,
                "predictions": top_items
            })

        log.info(f"  Batch {batch_num+1}/{n_batches} — {end}/{n_test} clientes procesados")

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

    # 1. Cargamos los datos limpios (ya divididos por tu árbitro)
    train, test, interactions = load_data()

    # 2. Construimos la matriz directamente con las interacciones seguras
    matrix, customer_idx, article_idx = build_user_item_matrix(interactions)

    # 3. Solo predecimos para clientes que tienen compras en test
    test_customer_ids = list(test["customer_id"].unique())

    recommendations = predict_for_test_users(
        matrix, customer_idx, article_idx,
        test_customer_ids=test_customer_ids,
        top_k=TOP_K, n_neighbors=N_NEIGHBORS, batch_size=BATCH_SIZE
    )

    # 4. Evaluamos y guardamos
    metrics = evaluate(recommendations, test)
    save_results(recommendations, metrics)

    log.info("=" * 55)
    log.info(f"RESULTADO FINAL  →  MAP@12: {metrics['map_at_12']:.4f}")
    log.info(f"Cold Start:          {metrics['cold_start']:,} clientes sin predicción")
    log.info("=" * 55)

if __name__ == "__main__":
    main()
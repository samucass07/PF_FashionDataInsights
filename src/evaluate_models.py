import pandas as pd
import numpy as np
from config import PROCESSED_DIR, setup_logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
TOP_K = 12

log = setup_logging()

# ─────────────────────────────────────────────
# FUNCIONES MATEMÁTICAS (MÉTRICAS)
# ─────────────────────────────────────────────

def average_precision_at_k(predicted, actual, k=12):
    if not actual or not predicted: return 0.0
    predicted = predicted[:k]
    hits, score = 0, 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            hits += 1
            score += hits / (i + 1)
    return score / min(len(actual), k)

def precision_at_k(predicted, actual, k=12):
    if not actual or not predicted: return 0.0
    predicted = predicted[:k]
    hits = len(set(predicted).intersection(set(actual)))
    return hits / k

def recall_at_k(predicted, actual, k=12):
    if not actual or not predicted: return 0.0
    predicted = predicted[:k]
    hits = len(set(predicted).intersection(set(actual)))
    return hits / len(actual)

def ndcg_at_k(predicted, actual, k=12):
    if not actual or not predicted: return 0.0
    predicted = predicted[:k]
    dcg = 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            dcg += 1.0 / np.log2(i + 2)
    idcg = 0.0
    for i in range(min(len(actual), k)):
        idcg += 1.0 / np.log2(i + 2)
    if idcg == 0: return 0.0
    return dcg / idcg

# ─────────────────────────────────────────────
# JUEZ CENTRAL
# ─────────────────────────────────────────────

def run_evaluation():
    log.info("=" * 60)
    log.info("EVALUADOR CENTRAL DE MODELOS - TABLERO COMPLETO")
    log.info("=" * 60)

    # 1. Cargar ground truth
    test = pd.read_csv(
        PROCESSED_DIR / "test_transactions.csv",
        dtype={'customer_id': str, 'article_id': str}
    )
    ground_truth = test.groupby("customer_id")["article_id"].apply(list).to_dict()
    log.info(f"Total de clientes a evaluar: {len(ground_truth):,}")

    # 2. Modelos a evaluar
    modelos_a_evaluar = {
        "Modelo 1 (Popularidad)":  "recommendations_model1.csv",
        "Modelo 2 (Colaborativo)": "recommendations_model2.csv",
        "Modelo Híbrido":          "recommendations_hybrid.csv"
    }

    # 3. Lista para acumular métricas de todos los modelos
    all_metrics = []

    for nombre_modelo, archivo in modelos_a_evaluar.items():
        ruta_archivo = PROCESSED_DIR / archivo

        if not ruta_archivo.exists():
            log.warning(f"No se encontró el archivo: {archivo}")
            continue

        log.info("-" * 60)
        log.info(f"Evaluando: {nombre_modelo}")

        recs = pd.read_csv(ruta_archivo, dtype={'customer_id': str, 'article_id': str})
        predictions = recs.groupby("customer_id")["article_id"].apply(list).to_dict()

        ap_scores, prec_scores, rec_scores, ndcg_scores = [], [], [], []
        clientes_sin_pred = 0

        for customer_id, actual in ground_truth.items():
            pred = predictions.get(customer_id, [])
            if not pred:
                clientes_sin_pred += 1
            ap_scores.append(average_precision_at_k(pred, actual, k=TOP_K))
            prec_scores.append(precision_at_k(pred, actual, k=TOP_K))
            rec_scores.append(recall_at_k(pred, actual, k=TOP_K))
            ndcg_scores.append(ndcg_at_k(pred, actual, k=TOP_K))

        map_score = np.mean(ap_scores)
        mean_prec = np.mean(prec_scores)
        mean_rec  = np.mean(rec_scores)
        mean_ndcg = np.mean(ndcg_scores)
        coverage  = len([s for s in ap_scores if s > 0]) / len(ap_scores) * 100

        log.info(f"  MAP@{TOP_K}:       {map_score:.5f}")
        log.info(f"  NDCG@{TOP_K}:      {mean_ndcg:.5f}")
        log.info(f"  Precision@{TOP_K}: {mean_prec:.5f}")
        log.info(f"  Recall@{TOP_K}:    {mean_rec:.5f}")
        log.info(f"  Cobertura:      {coverage:.2f}% clientes con al menos 1 hit")
        log.info(f"  Cold Start:     {clientes_sin_pred:,} clientes sin predicción")

        # Acumular métricas
        all_metrics.append({
            "model":        nombre_modelo,
            "map_at_12":    round(map_score, 5),
            "ndcg_at_12":   round(mean_ndcg, 5),
            "precision_at_12": round(mean_prec, 5),
            "recall_at_12": round(mean_rec, 5),
            "coverage_pct": round(coverage, 2),
            "cold_start":   clientes_sin_pred
        })

    # 4. Guardar CSV con métricas de todos los modelos
    if all_metrics:
        metrics_df = pd.DataFrame(all_metrics)
        path_metrics = PROCESSED_DIR / "metrics_all_models.csv"
        metrics_df.to_csv(path_metrics, index=False,decimal=",")
        log.info("=" * 60)
        log.info(f"Métricas guardadas en: {path_metrics}")
        log.info("=" * 60)

if __name__ == "__main__":
    run_evaluation()
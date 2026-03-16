import pandas as pd
import numpy as np
import os
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
PROCESSED_PATH = "data/processed"
TOP_K = 12

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

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
    
    # Calcular el DCG (Discounted Cumulative Gain)
    dcg = 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            # i es base 0, por lo que sumamos 2 para que el primer rango divida por log2(2)=1
            dcg += 1.0 / np.log2(i + 2)
            
    # Calcular el IDCG (Ideal DCG - si todos los aciertos estuvieran al principio)
    idcg = 0.0
    for i in range(min(len(actual), k)):
        idcg += 1.0 / np.log2(i + 2)
        
    if idcg == 0: return 0.0
    return dcg / idcg

# ─────────────────────────────────────────────
# JUEZ CENTRAL
# ─────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("EVALUADOR CENTRAL DE MODELOS - TABLERO COMPLETO")
    log.info("=" * 60)

    # 1. Cargar el "Examen" (Ground Truth)
    test_path = os.path.join(PROCESSED_PATH, "test_transactions.csv")
    log.info("Cargando respuestas correctas (Test)...")
    test = pd.read_csv(test_path, dtype={'customer_id': str, 'article_id': str})
    
    ground_truth = test.groupby("customer_id")["article_id"].apply(list).to_dict()
    log.info(f"Total de clientes a evaluar: {len(ground_truth):,}")

    # 2. Archivos a evaluar
    modelos_a_evaluar = {
        "Modelo 1 (Popularidad)": "recommendations_model1.csv",
        "Modelo 2 (Colaborativo)": "recommendations_model2.csv",
        "Modelo Híbrido": "recommendations_hybrid.csv"
    }

    for nombre_modelo, archivo in modelos_a_evaluar.items():
        ruta_archivo = os.path.join(PROCESSED_PATH, archivo)
        
        if not os.path.exists(ruta_archivo):
            log.warning(f"No se encontró el archivo: {archivo}")
            continue

        log.info("-" * 60)
        log.info(f"Evaluando: {nombre_modelo}")
        
        recs = pd.read_csv(ruta_archivo, dtype={'customer_id': str, 'article_id': str})
        predictions = recs.groupby("customer_id")["article_id"].apply(list).to_dict()

        # Listas para guardar los scores de todos los clientes
        ap_scores   = []
        prec_scores = []
        rec_scores  = []
        ndcg_scores = []
        clientes_sin_pred = 0

        # Calcular todas las métricas por cliente
        for customer_id, actual in ground_truth.items():
            pred = predictions.get(customer_id, [])
            if not pred:
                clientes_sin_pred += 1
            
            ap_scores.append(average_precision_at_k(pred, actual, k=TOP_K))
            prec_scores.append(precision_at_k(pred, actual, k=TOP_K))
            rec_scores.append(recall_at_k(pred, actual, k=TOP_K))
            ndcg_scores.append(ndcg_at_k(pred, actual, k=TOP_K))

        # Promedios finales
        map_score  = np.mean(ap_scores)
        mean_prec  = np.mean(prec_scores)
        mean_rec   = np.mean(rec_scores)
        mean_ndcg  = np.mean(ndcg_scores)
        coverage   = len([s for s in ap_scores if s > 0]) / len(ap_scores) * 100

        # Mostrar resultados en el tablero
        log.info(f"  MAP@{TOP_K}:       {map_score:.5f}")
        log.info(f"  NDCG@{TOP_K}:      {mean_ndcg:.5f}")
        log.info(f"  Precision@{TOP_K}: {mean_prec:.5f}")
        log.info(f"  Recall@{TOP_K}:    {mean_rec:.5f}")
        log.info(f"  Cobertura:      {coverage:.2f}% clientes con al menos 1 hit")
        log.info(f"  Cold Start:     {clientes_sin_pred:,} clientes sin predicción")

    log.info("=" * 60)

if __name__ == "__main__":
    main()
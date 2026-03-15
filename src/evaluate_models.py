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

def average_precision_at_k(predicted, actual, k=12):
    """Calcula la precisión promedio para un solo cliente."""
    if not actual:
        return 0.0
    predicted = predicted[:k]
    hits, score = 0, 0.0
    for i, p in enumerate(predicted):
        if p in actual:
            hits += 1
            score += hits / (i + 1)
    return score / min(len(actual), k)

def main():
    log.info("=" * 55)
    log.info("EVALUADOR CENTRAL DE MODELOS")
    log.info("=" * 55)

    # 1. Cargar el "Examen" (Ground Truth)
    test_path = os.path.join(PROCESSED_PATH, "test_transactions.csv")
    log.info("Cargando respuestas correctas (Test)...")
    test = pd.read_csv(test_path, dtype={'customer_id': str, 'article_id': str})
    
    # Agrupamos qué compró realmente cada cliente en la semana de prueba
    ground_truth = test.groupby("customer_id")["article_id"].apply(list).to_dict()
    log.info(f"Total de clientes a evaluar: {len(ground_truth):,}")

    # 2. Archivos a evaluar
    modelos_a_evaluar = {
        "Modelo 1 (Popularidad)": "recommendations_model1.csv", # Cambiá este nombre si tu archivo se llama distinto
        "Modelo 2 (Colaborativo)": "recommendations_model2.csv"
        # "Modelo Híbrido": "recommendations_hybrid.csv"  <-- Lo dejamos listo para el final
    }

    for nombre_modelo, archivo in modelos_a_evaluar.items():
        ruta_archivo = os.path.join(PROCESSED_PATH, archivo)
        
        if not os.path.exists(ruta_archivo):
            log.warning(f"No se encontró el archivo para {nombre_modelo}: {archivo}")
            continue

        log.info("-" * 55)
        log.info(f"Evaluando: {nombre_modelo}")
        
        # Cargar predicciones
        recs = pd.read_csv(ruta_archivo, dtype={'customer_id': str, 'article_id': str})
        
        # Transformar de formato "explotado" a listas por cliente
        predictions = recs.groupby("customer_id")["article_id"].apply(list).to_dict()

        ap_scores = []
        clientes_sin_pred = 0

        # Calcular MAP@12
        for customer_id, actual in ground_truth.items():
            pred = predictions.get(customer_id, [])
            if not pred:
                clientes_sin_pred += 1
            
            ap = average_precision_at_k(pred, actual, k=TOP_K)
            ap_scores.append(ap)

        map_score = np.mean(ap_scores)
        coverage = len([s for s in ap_scores if s > 0]) / len(ap_scores) * 100

        log.info(f"  MAP@12:             {map_score:.4f}")
        log.info(f"  Cobertura:          {coverage:.1f}% con aciertos")
        log.info(f"  Cold Start (Vacío): {clientes_sin_pred:,} clientes")

    log.info("=" * 55)

if __name__ == "__main__":
    main()
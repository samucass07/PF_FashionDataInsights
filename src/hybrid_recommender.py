import pandas as pd
from config import PROCESSED_DIR, setup_logging

# Inicializamos el log estandarizado para Airflow
log = setup_logging()

def run_hybrid_model():
    """Función principal orquestable por Airflow."""
    log.info("=" * 55)
    log.info("CREANDO MODELO HÍBRIDO (Colaborativo + Popularidad)")
    log.info("=" * 55)

    # 1. Cargar predicciones de los modelos base
    log.info("Cargando predicciones de los modelos base...")
    # Usamos pathlib de config.py
    m1 = pd.read_csv(PROCESSED_DIR / "recommendations_model1.csv", dtype=str)
    m2 = pd.read_csv(PROCESSED_DIR / "recommendations_model2.csv", dtype=str)

    log.info("Optimizando estructuras...")
    # Convertir a diccionarios para acceso instantáneo
    dict_m1 = m1.groupby("customer_id")["article_id"].apply(list).to_dict()
    dict_m2 = m2.groupby("customer_id")["article_id"].apply(list).to_dict()

    # 2. Cargar Test (A quiénes les vamos a recomendar)
    test_path = PROCESSED_DIR / "test_transactions.csv"
    test_df = pd.read_csv(test_path, dtype={'customer_id': str})
    clientes_a_predecir = test_df['customer_id'].unique()

    log.info("Ensamblando recomendaciones híbridas...")
    hybrid_recs = []

    # 3. Lógica de ensamblado
    for cust_id in clientes_a_predecir:
        recs_finales = []
        vistos = set()

        # A) Prioridad 1: Colaborativo (Gustos personales)
        if cust_id in dict_m2:
            for art in dict_m2[cust_id]:
                if len(recs_finales) >= 12: break
                if art not in vistos:
                    vistos.add(art)
                    recs_finales.append(art)

        # B) Prioridad 2: Rellenar con Popularidad (Tendencias)
        if len(recs_finales) < 12 and cust_id in dict_m1:
            for art in dict_m1[cust_id]:
                if len(recs_finales) >= 12: break
                if art not in vistos:
                    vistos.add(art)
                    recs_finales.append(art)

        hybrid_recs.append({
            "customer_id": cust_id,
            "predictions": recs_finales
        })

    # 4. Guardar archivo final
    log.info("Guardando archivo de recomendaciones híbridas...")
    df_hybrid = pd.DataFrame(hybrid_recs)
    recs_exploded = df_hybrid.explode("predictions").rename(columns={"predictions": "article_id"})
    
    path_r = PROCESSED_DIR / "recommendations_hybrid.csv"
    recs_exploded.to_csv(path_r, index=False)

    log.info(f"¡Éxito! Archivo guardado en: {path_r}")
    log.info("=" * 55)

if __name__ == "__main__":
    run_hybrid_model()
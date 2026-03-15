import pandas as pd
import os
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
PROCESSED_PATH = "data/processed"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

def main():
    log.info("=" * 55)
    log.info("CREANDO MODELO HÍBRIDO (Colaborativo + Popularidad)")
    log.info("=" * 55)

    # 1. Cargar predicciones de los modelos base
    log.info("Cargando predicciones de los modelos base...")
    m1 = pd.read_csv(os.path.join(PROCESSED_PATH, "recommendations_model1.csv"), dtype=str)
    m2 = pd.read_csv(os.path.join(PROCESSED_PATH, "recommendations_model2.csv"), dtype=str)

    log.info("Optimizando estructuras...")
    # Convertir a diccionarios para acceso instantáneo
    dict_m1 = m1.groupby("customer_id")["article_id"].apply(list).to_dict()
    dict_m2 = m2.groupby("customer_id")["article_id"].apply(list).to_dict()

    # 2. Cargar Test (A quiénes les vamos a recomendar)
    test_path = os.path.join(PROCESSED_PATH, "test_transactions.csv")
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
    
    path_r = os.path.join(PROCESSED_PATH, "recommendations_hybrid.csv")
    recs_exploded.to_csv(path_r, index=False)

    log.info(f"¡Éxito! Archivo guardado en: {path_r}")
    log.info("=" * 55)

if __name__ == "__main__":
    main()
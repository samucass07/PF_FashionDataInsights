import pandas as pd
from config import PROCESSED_DIR, setup_logging

# Inicializamos el log estandarizado para Airflow
log = setup_logging()

# ─────────────────────────────────────────────
# CARGA DE DATOS EN MEMORIA (BLINDADO CON DTYPES)
# ─────────────────────────────────────────────
def load_model_data():
    log.info("Cargando motores del Modelo 1 en memoria RAM...")
    try:
        # FORZAMOS STRING para no perder los ceros a la izquierda de los IDs
        # Usamos pathlib para acceder a las rutas limpiamente
        df_customers = pd.read_csv(PROCESSED_DIR / "features_customers.csv", dtype={'customer_id': str})
        df_popularity = pd.read_csv(PROCESSED_DIR / "gen_popularity.csv", dtype={'article_id': str})
        df_articles = pd.read_csv(PROCESSED_DIR / "features_articles.csv", dtype={'article_id': str})
        return df_customers, df_popularity, df_articles
    except FileNotFoundError as e:
        log.error(f"Error crítico: Faltan archivos en {PROCESSED_DIR}.")
        raise e

# ─────────────────────────────────────────────
# MAIN REFACTOREADO PARA MLOPS
# ─────────────────────────────────────────────
def run_popularity_model():
    """Función principal orquestable por Airflow."""
    log.info("=" * 55)
    log.info("MODELO 1 — Popularidad por Generación (PRODUCCIÓN)")
    log.info("=" * 55)

    # 1. Cargar datos base
    df_customers, df_popularity, df_articles = load_model_data()

    # 2. Cargar Test (A quiénes les vamos a recomendar)
    test_path = PROCESSED_DIR / "test_transactions.csv"
    test_df = pd.read_csv(test_path, dtype={'customer_id': str, 'article_id': str})
    clientes_a_predecir = test_df['customer_id'].unique()

    log.info("Construyendo diccionarios de alta velocidad (Complejidad O(1))...")

    # 3. CONSTRUCCIÓN DE DICCIONARIOS
    # A. Diccionario: Cliente -> Su Generación
    cust_to_gen = dict(zip(df_customers["customer_id"], df_customers["age_group"]))

    # B. Diccionario: Artículo -> Nombre (Para que no recomiende el mismo producto 2 veces)
    art_to_name = dict(zip(df_articles["article_id"], df_articles["prod_name"]))

    # C. Diccionario: Generación -> Lista de IDs de artículos más populares de esa gen
    gen_to_pop = (
        df_popularity.sort_values(["age_group", "rank_in_generation"])
        .groupby("age_group")["article_id"]
        .apply(list)
        .to_dict()
    )

    # D. Lista: Top Global absoluto (El paracaídas de emergencia / Cold Start)
    global_top = df_articles.sort_values("global_rank")["article_id"].tolist()

    log.info(f"Generando recomendaciones para {len(clientes_a_predecir):,} clientes...")

    todas_las_recomendaciones = []

    # 4. LOOP DE PREDICCIÓN 
    for customer_id in clientes_a_predecir:
        gen = cust_to_gen.get(customer_id)
        candidatos_gen = gen_to_pop.get(gen, [])
        
        recomendaciones_finales = []
        nombres_vistos = set()

        # A) Primero intentamos llenar los 12 con su Generación
        for art_id in candidatos_gen:
            if len(recomendaciones_finales) >= 12:
                break
            
            nombre = art_to_name.get(art_id, f"Desconocido_{art_id}")
            if nombre not in nombres_vistos:
                nombres_vistos.add(nombre)
                recomendaciones_finales.append(art_id)

        # B) Si no llegamos a 12 (Cold Start o pocos productos), rellenamos con el Top Global
        if len(recomendaciones_finales) < 12:
            for art_id in global_top:
                if len(recomendaciones_finales) >= 12:
                    break
                
                nombre = art_to_name.get(art_id, f"Desconocido_{art_id}")
                if nombre not in nombres_vistos:
                    nombres_vistos.add(nombre)
                    recomendaciones_finales.append(art_id)

        # Guardamos el resultado del cliente
        todas_las_recomendaciones.append({
            "customer_id": customer_id,
            "predictions": recomendaciones_finales
        })

    # 5. GUARDAR RESULTADOS
    log.info("Guardando archivo de recomendaciones...")
    df_recs = pd.DataFrame(todas_las_recomendaciones)
    recs_exploded = df_recs.explode("predictions").rename(columns={"predictions": "article_id"})
    
    path_r = PROCESSED_DIR / "recommendations_model1.csv"
    recs_exploded.to_csv(path_r, index=False)

    log.info(f"¡Éxito! Archivo guardado en: {path_r}")
    log.info("=" * 55)

if __name__ == "__main__":
    run_popularity_model()
import pandas as pd
import os
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
PROCESSED_PATH = "data/processed"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CARGA DE DATOS EN MEMORIA
# ─────────────────────────────────────────────

def load_model_data():
    """
    Carga los datasets procesados en memoria RAM.
    Retorna las tres tablas necesarias para el modelo.
    """
    log.info("Cargando motores del Modelo 1 en memoria RAM...")
    
    try:
        # 1. Clientes (para saber su generación)
        customers_df = pd.read_csv(os.path.join(PROCESSED_PATH, "features_customers.csv"))
        
        # 2. Ranking por generación (el motor principal)
        popularity_df = pd.read_csv(os.path.join(PROCESSED_PATH, "gen_popularity.csv"))
        
        # 3. Artículos (para el Top 90 días global en caso de Cold Start)
        articles_df = pd.read_csv(os.path.join(PROCESSED_PATH, "features_articles.csv"))
        
        log.info(f"Datos listos: Clientes({len(customers_df)}), PopGen({len(popularity_df)}), Artículos({len(articles_df)})")
        
        return customers_df, popularity_df, articles_df
        
    except FileNotFoundError as e:
        log.error(f"Error crítico: Faltan archivos en {PROCESSED_PATH}. ¿Ejecutaste el Feature Engineering?")
        raise e

# ─────────────────────────────────────────────
# LÓGICA DE RECOMENDACIÓN
# ─────────────────────────────────────────────

def recommend(customer_id, customers_df, popularity_df, articles_df, n=12):
    """
    Recomienda los N artículos más populares para la generación del cliente.
    Evita recomendar el mismo modelo de producto en distintos colores.
    """
    # 1. Preparar listas completas ordenadas
    global_top = articles_df.sort_values("global_rank")["article_id"].tolist()
    
    # Buscar al cliente
    customer_data = customers_df[customers_df["customer_id"] == customer_id]
    
    # 2. Obtener los candidatos (Generación o Global si hay Cold Start)
    if customer_data.empty or pd.isna(customer_data["age_group"].values[0]):
        log.info(f"Cold Start para {str(customer_id)[-6:]}: Usando Top Global.")
        candidatos = global_top
    else:
        gen = customer_data["age_group"].values[0]
        gen_data = popularity_df[popularity_df["age_group"] == gen]
        candidatos_gen = gen_data.sort_values("rank_in_generation")["article_id"].tolist()
        
        # Unimos su generación con el global (por si su generación compró muy poco)
        candidatos = candidatos_gen + [art for art in global_top if art not in candidatos_gen]

    # 3. Filtro de Negocio: Deduplicación por nombre de producto
    recomendaciones_finales = []
    nombres_vistos = set()
    
    for articulo_id in candidatos:
        # Si ya llegamos a N recomendaciones distintas, cortamos el ciclo
        if len(recomendaciones_finales) >= n:
            break
            
        # Buscamos el nombre del artículo actual en la memoria RAM
        datos_articulo = articles_df[articles_df["article_id"] == articulo_id]
        
        # Cambiá "prod_name" si tu columna se llama diferente en articles_clean.csv
        if not datos_articulo.empty and "prod_name" in datos_articulo.columns:
            nombre = datos_articulo["prod_name"].values[0]
        else:
            nombre = f"Desconocido_{articulo_id}"
            
        # Solo lo agregamos a la lista final si es un nombre nuevo
        if nombre not in nombres_vistos:
            nombres_vistos.add(nombre)
            recomendaciones_finales.append(articulo_id)

    # Si por algún motivo extremo no llegamos a N, avisamos en el log
    if len(recomendaciones_finales) < n:
        log.warning(f"Solo se encontraron {len(recomendaciones_finales)} productos únicos para recomendar.")

    return recomendaciones_finales

# ─────────────────────────────────────────────
# GENERAR PREDICCIONES Y GUARDAR (MAIN)
# ─────────────────────────────────────────────

def save_results(recommendations_list):
    """Guarda las recomendaciones en formato 'explotado' (una fila por artículo)."""
    df = pd.DataFrame(recommendations_list)
    recs_exploded = df.explode("predictions").rename(columns={"predictions": "article_id"})
    
    path_r = os.path.join(PROCESSED_PATH, "recommendations_model1.csv")
    recs_exploded.to_csv(path_r, index=False)
    log.info(f"Recomendaciones Modelo 1 guardadas en: {path_r}")

if __name__ == "__main__":
    log.info("=" * 55)
    log.info("MODELO 1 — Popularidad por Generación")
    log.info("=" * 55)

    # 1. Cargamos los datos en la memoria RAM
    df_customers, df_popularity, df_articles = load_model_data()
    
    # 2. Cargamos el test para saber a qué clientes predecirle
    test_path = os.path.join(PROCESSED_PATH, "test_transactions.csv")
    test_df = pd.read_csv(test_path, dtype={'customer_id': str, 'article_id': str})
    clientes_a_predecir = test_df['customer_id'].unique()
    
    log.info(f"Generando recomendaciones para {len(clientes_a_predecir):,} clientes del Test...")
    
    # 3. Calculamos recomendaciones para todos los clientes (ESTO PUEDE TARDAR UNOS MINUTOS)
    todas_las_recomendaciones = []
    
    for i, customer_id in enumerate(clientes_a_predecir):
        rec = recommend(
            customer_id=customer_id, 
            customers_df=df_customers, 
            popularity_df=df_popularity, 
            articles_df=df_articles,
            n=12
        )
        
        todas_las_recomendaciones.append({
            "customer_id": customer_id,
            "predictions": rec
        })
        
        # Un simple log para ver que el código avanza
        if (i + 1) % 1000 == 0:
            log.info(f"  Procesados {i+1} de {len(clientes_a_predecir)} clientes...")

    # 4. Guardar archivo final
    save_results(todas_las_recomendaciones)
    log.info("=" * 55)
    log.info("¡Modelo 1 finalizado!")
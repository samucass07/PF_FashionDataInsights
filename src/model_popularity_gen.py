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
# PRUEBA LOCAL (MAIN)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("INICIANDO PRUEBA DEL MODELO 1")
    log.info("=" * 50)

    # 1. Cargamos los datos en la memoria RAM (solo se hace una vez)
    df_customers, df_popularity, df_articles = load_model_data()

    # 2. Elegimos un cliente de prueba dinámicamente
    # En lugar de hardcodear un ID, tomamos el primero que aparezca en el dataset
    # para asegurarnos de que el código no tire error por no encontrarlo.
    test_customer_id = df_customers["customer_id"].iloc[0]
    
    # También podés probar el Cold Start descomentando esta línea:
    # test_customer_id = "cliente_fantasma_123"

    log.info(f"Generando recomendaciones para el cliente: {test_customer_id}")

    # 3. Llamamos a la función matemática pasándole los datos en memoria
    recomendaciones = recommend(
        customer_id=test_customer_id, 
        customers_df=df_customers, 
        popularity_df=df_popularity, 
        articles_df=df_articles,
        n=12
    )

    # 4. Mostramos el resultado con los nombres reales
    print("\n" + "-" * 60)
    print(f" TOP 12 RECOMENDACIONES PARA EL CLIENTE ")
    print("-" * 60)
    
    for i, articulo_id in enumerate(recomendaciones, 1):
        # Buscamos la fila del artículo en nuestro DataFrame cargado en RAM
        datos_articulo = df_articles[df_articles["article_id"] == articulo_id]
        
        # Extraemos el nombre. 
        # NOTA: Cambiá "prod_name" por el nombre exacto de la columna en tu dataset
        # (A veces suele llamarse "detail_desc", "product_type_name", etc.)
        if not datos_articulo.empty and "prod_name" in datos_articulo.columns:
            nombre = datos_articulo["prod_name"].values[0]
        else:
            nombre = "Descripción no disponible"
            
        print(f" {i:02d}. ID: {articulo_id} | Producto: {nombre}")
        
    print("-" * 60 + "\n")
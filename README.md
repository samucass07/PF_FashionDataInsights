# H&M Fashion Recommendations - Data Engineering Pipeline

¡Bienvenido al repositorio central de nuestro proyecto de análisis de datos! Este trabajo es una colaboración conjunta diseñada para transformar datos crudos del sector retail en información estructurada y lista para modelos de Inteligencia Artificial.

---

## Objetivo del Proyecto
Desarrollar un sistema de recomendación híbrido capaz de predecir, para cada cliente, los 12 artículos con mayor probabilidad de compra en el próximo período.

---

## Estructura del Repositorio
Para que el proyecto sea fácil de navegar, hemos organizado las carpetas de la siguiente manera:

* **`App/`**: La interfaz de usuario.
* **`data/`**: El almacén de datos.
    * **`raw/`**: Archivos originales descargados directamente de la fuente.
    * **`processed/`**: Archivos con los datos limpios y optimizados.
* **`notebooks/`**: Notebooks de Jupyter con el proceso de exploración de datos.
* **`reports/`**: Informes de resultados y conclusiones. 
* **`src/`**: Contiene el motor del proyecto (scripts ETL, Feature Engineering y Modelos).
* **`venv/`**: Nuestro entorno virtual para asegurar que las herramientas siempre funcionen correctamente.

## 1. El Corazón de los Datos (Dataset)
Trabajamos con tres pilares fundamentales de información proporcionados por H&M:

1.  **Clientes (`customers.csv`)**: Perfiles de **1.37 millones** de personas, incluyendo su edad y estado de membresía.
2.  **Artículos (`articles.csv`)**: Un catálogo de **105,542** prendas de vestir con detalles como color y tipo de producto.
3.  **Transacciones (`transactions_train.csv`)**: El registro masivo de más de **31 millones** de compras realizadas históricamente.

---

## 2. El Proceso de Limpieza (ETL)
El archivo `src/etl.py` es nuestra solución de ingeniería. Transforma los datos gigantes en archivos manejables y optimizados.

**¿Qué hace exactamente este proceso?**
* **Muestreo Inteligente**: Para que el desarrollo sea ágil, seleccionamos aleatoriamente al 10% de los clientes (aprox. 137,000) y mantenemos **todo** su historial de compras.
* **Imputación de Datos**: Completamos las edades faltantes usando la **mediana** (el valor central) para no distorsionar las estadísticas.
* **Optimización de RAM**: Cambiamos la forma en que la computadora lee los números para que ocupen un 60% menos de espacio en la memoria.
* **Integridad Referencial**: Nos aseguramos de que no existan compras de productos que no estén en el catálogo oficial.

[Ver informe completo ETL](https://github.com/samucass07/PF_FashionDataInsights/tree/main/reports/ETL/ETL.md)

## 3. Análisis Exploratorio (EDA)
El archivo contiene la revisión y análisis del comportamiento inicial del dataset. En él se explora:
* Estructura y tipos de datos de cada tabla (`customers`, `articles`, `transactions`)
* Valores faltantes
* Distribución de variables
* Relaciones entre variables
* Estadísticas descriptivas
* Correlaciones y patrones

[Ver informe completo EDA](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/EDA/EDA.md)

## 4. Ingeniería de Características (Feature Engineering)
El archivo `src/ft_engineering.py` toma los datos limpios y crea las variables ("features") necesarias para alimentar los modelos de Machine Learning. El pipeline genera 4 pilares de datos:

* **Segmentación Demográfica**: Agrupación de clientes en Gen Z, Millennials, Gen X y Seniors.
* **Comportamiento del Cliente (RFM)**: Cálculo de Recencia, Frecuencia y canal de compra preferido, con manejo avanzado de *Cold Start* para clientes sin compras previas.
* **Tendencias Recientes**: Popularidad de artículos a nivel global y por generación, aplicando una **ventana de tiempo de 90 días**.
* **Matriz de Interacciones**: Puente hacia el filtrado colaborativo, eliminando el ruido al conservar únicamente clientes con un historial mínimo de compras (>2).

---

## 5. Modelos de Recomendación

Hemos diseñado una arquitectura modular basada en múltiples enfoques algorítmicos para capturar diferentes comportamientos de compra:

### Modelo 1: Popularidad por Generación (`model_popularity_gen.py`)
Actúa como un *baseline* extremadamente sólido para el sector de Fast Fashion (basado en tendencias masivas).
* **In-Memory Processing**: Uso de diccionarios de alta velocidad O(1) para procesar a todos los clientes en segundos.
* **Manejo de Cold Start**: "Fallback" seguro ofreciendo los productos más vendidos a nivel global para clientes sin historial.
* **Regla de Negocio (Deduplicación)**: Implementa un filtro que evita recomendar el mismo modelo de prenda en distintos colores.

### Modelo 2: Filtrado Colaborativo basado en Usuarios (`model_collaborative.py`)
Captura preferencias de nicho buscando clientes con historiales de compra similares.
* **Matriz Dispersa (Sparse Matrix)**: Optimización extrema de memoria usando `scipy.sparse` para calcular la similitud del coseno.
* **Custom Grid Search**: Búsqueda automatizada de hiperparámetros que itera, evalúa y guarda dinámicamente el mejor modelo. Se determinó que el rendimiento óptimo se alcanza con **`N_NEIGHBORS = 200`**.

### Orquestador Híbrido (`hybrid_recommender.py`)
Un sistema ensamblador que fusiona lo mejor de ambos mundos:
* Da prioridad a las recomendaciones personalizadas del Modelo 2 (Colaborativo).
* Rellena automáticamente los huecos vacíos y rescata a los clientes afectados por el *Cold Start* inyectando las tendencias del Modelo 1 (Popularidad), garantizando un vector estricto de 12 predicciones por cliente.

---

## 6. Juez Central y Métricas Avanzadas (`evaluate_models.py`)

Para garantizar que el modelo sea auditable y profesional, se construyó un script evaluador independiente. Esto previene el *Data Leakage* al separar estrictamente los datos de entrenamiento de los datos de prueba ciegos (Test). 

Se implementaron métricas estándar de la industria para sistemas de recomendación (Ranking):
* **MAP@12 (Mean Average Precision)**: Mide la precisión global teniendo en cuenta la posición de los aciertos.
* **NDCG@12 (Normalized Discounted Cumulative Gain)**: Métrica suprema de ordenamiento; penaliza severamente si un acierto se encuentra al final de las recomendaciones en lugar de al principio.
* **Precision@12 y Recall@12**: Permiten auditar qué tan "limpias" son las sugerencias y qué porcentaje del historial real del cliente logramos capturar.
* **Cobertura**: Monitoreo de *Cold Start* y porcentaje de clientes con al menos un acierto.

---

## 7. Cómo empezar (Instalación y Ejecución)

Si quieres replicar este proyecto en tu entorno local, sigue estos pasos:

```bash
# 1. Activar el entorno virtual (Recomendado)
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
# source venv/bin/activate

# 2. Instalar las herramientas y dependencias necesarias
pip install pandas numpy scikit-learn scipy
# O instalar mediante el archivo de requerimientos si está disponible:
# pip install -r requirements.txt

# 3. Ejecutar el pipeline de datos y preparar el terreno
python src/etl.py
python src/ft_engineering.py
python src/train_test_split.py

# 4. Generar las predicciones
python src/model_popularity_gen.py
python src/model_collaborative.py
python src/hybrid_recommender.py

# 5. Evaluar el rendimiento de los modelos
python src/evaluate_models.py

## Presentaciones
* [Presentación 1](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/EDA/EDA.md)

## Autores
Este es un proyecto desarrollado por:
* **Tobias Dagrava**: Estudiante de Ingeniería en Sistemas (UTN - FRLP), con especialización en Data Science y modelado de datos.
* **Samuel**: Desarrollador, colaborador y encargado de la gestión del repositorio y sincronización de datos.
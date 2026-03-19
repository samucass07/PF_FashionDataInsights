# H&M Fashion Recommendations - Data Engineering Pipeline

¡Bienvenido al repositorio central de nuestro proyecto de análisis de datos! Este trabajo es una colaboración conjunta diseñada para transformar datos crudos del sector retail en información estructurada y lista para modelos de Inteligencia Artificial.

---

## Objetivo del Proyecto
Desarrollar un sistema de recomendación híbrido capaz de predecir, para cada cliente, los 12 artículos con mayor probabilidad de compra en el próximo período.

---

---

## Fuente de Datos
El dataset utilizado en este proyecto proviene de la competición oficial de Kaggle: [H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data).

---

## Estructura del Repositorio

Para que el proyecto sea fácil de navegar, hemos organizado las carpetas de la siguiente manera:

```
PF_FashionDataInsights/
├── App/
│   ├── frontend.py
│   └── main.py
├── dags/
│   └── fashion_pipeline_dag.py
├── data/
│   ├── raw/                        ← archivos originales de Kaggle (no versionados)
│   └── processed/                  ← CSVs limpios y features (no versionados)
├── logs/                           ← logs generados por Airflow (no versionados)
├── Notebooks/
│   ├── eda_inicial.ipynb
│   └── eda_profundo.ipynb
├── reports/
│                    
├── src/
│   ├── config.py
│   ├── etl.py
│   ├── train_test_split.py
│   ├── ft_engineering.py
│   ├── model_popularity_gen.py
│   ├── model_collaborative.py
│   ├── hybrid_recommender.py
│   ├── evaluate_models.py
│   └── fix_rank.py
├── docker-compose.yml
└── README.md
```

### App/
| Archivo | Descripción |
|---|---|
| `frontend.py` | Interfaz de usuario construida con Streamlit. Permite buscar un cliente por ID y visualizar sus 12 recomendaciones personalizadas. |
| `main.py` | API backend construida con FastAPI. Recibe el `customer_id`, consulta el modelo ganador y devuelve las recomendaciones en formato JSON. |

### dags/
| Archivo | Descripción |
|---|---|
| `fashion_pipeline_dag.py` | DAG de Apache Airflow que orquesta el pipeline completo de extremo a extremo: ETL → Feature Engineering → Split → Modelos → Evaluación. Contenedorizado con Docker. |

### Notebooks/
| Archivo | Descripción |
|---|---|
| `eda_inicial.ipynb` | Exploración inicial del dataset. Verificación de tipos de datos, valores nulos, distribuciones básicas y primeras estadísticas descriptivas. |
| `eda_profundo.ipynb` | Análisis exploratorio detallado. Segmentación por generación, preferencias de color por género, evolución de ventas diarias, análisis estacional y top artículos por segmento. |

### src/
| Archivo | Descripción |
|---|---|
| `config.py` | Configuración centralizada del proyecto: rutas de directorios, parámetros globales y setup del sistema de logging estandarizado para Airflow. |
| `etl.py` | Pipeline de Extracción, Transformación y Carga. Lee las 31M transacciones por chunks, samplea el 5% de clientes, limpia las 3 tablas y exporta los CSVs limpios. |
| `train_test_split.py` | Divide las transacciones en train y test usando un split temporal (últimas semanas como test). Evita data leakage al no usar split aleatorio. |
| `ft_engineering.py` | Pipeline de Feature Engineering. Genera 4 grupos de features: segmentación demográfica (age_group), comportamiento RFM del cliente, tendencias recientes por ventana de 90 días, y matriz de interacciones. |
| `model_popularity_gen.py` | Modelo 1 — Popularity Generation-Based. Recomienda los 12 artículos más populares dentro de la generación del cliente. Baseline interpretable sin cold start. |
| `model_collaborative.py` | Modelo 2 — User-Based Collaborative Filtering. Encuentra los 20 vecinos más similares por similitud coseno y recomienda artículos que esos vecinos compraron. Implementado con batch processing para manejar 135k clientes. |
| `hybrid_recommender.py` | Modelo Híbrido. Fusiona el colaborativo y el de popularidad: prioriza recomendaciones personalizadas del colaborativo y rellena huecos con tendencias por generación, garantizando 12 predicciones por cliente. |
| `evaluate_models.py` | Evaluador central de los 3 modelos. Calcula MAP@12, NDCG@12, Precision@12, Recall@12, Cobertura y Cold Start. Genera `metrics_all_models.csv` como única fuente de verdad. |
| `fix_rank.py` | Script utilitario. Agrega la columna `rank` (1-12 por cliente) a los CSVs de recomendaciones para uso en el dashboard de Power BI. |

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

[Ver informe completo ETL](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/ETL/README.md)

## 3. Análisis Exploratorio (EDA)
El archivo contiene la revisión y análisis del comportamiento inicial del dataset. En él se explora:
* Estructura y tipos de datos de cada tabla (`customers`, `articles`, `transactions`)
* Valores faltantes
* Distribución de variables
* Relaciones entre variables
* Estadísticas descriptivas
* Correlaciones y patrones

[Ver informe completo EDA](https://github.com/samucass07/PF_FashionDataInsights/tree/main/reports/EDA)

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

7. Arquitectura de Datos y Orquestación (Airflow)

El flujo de datos no es un proceso estático; se diseñó un pipeline automatizado utilizando **Apache Airflow** para garantizar que el modelo siempre trabaje con información íntegra y actualizada.

* **Orquestación mediante DAGs**: Se implementó un grafo acíclico dirigido que coordina las tareas de extracción, limpieza profunda y generación de archivos optimizados.
* **Resiliencia y Monitoreo**: Gracias al scheduler de Airflow, el sistema cuenta con logs detallados por cada etapa y políticas de reintento automático ante fallos de recursos.
* **Eficiencia**: El pipeline transforma los archivos originales en formatos **Parquet**, permitiendo una carga de datos mucho más veloz para los servicios de inferencia.

[Ver informe completo de Orquestación](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/AIRFLOW/README.md)

---

# 8. Implementación de Servicios (FastAPI & Streamlit)

Para transformar el modelo en una herramienta accionable, se desarrolló una arquitectura de servicios desacoplada:

* **Backend (FastAPI)**: Un servicio de alta velocidad que expone el motor de recomendación. Utiliza validación de tipos con **Pydantic** y ofrece documentación interactiva automática en `/docs`.
* **Frontend (Streamlit)**: Una interfaz de usuario diseñada para la exploración de resultados. Permite consultar recomendaciones personalizadas por cliente y visualizar tendencias de productos en tiempo real mediante gráficos interactivos.
* **Comunicación**: La aplicación consume la API de forma asincrónica, delegando la lógica pesada de datos al servidor para mantener una interfaz fluida.

[Ver informe completo de Aplicación](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/FASTAPI-STREAMLIT/README.md)

---

# 9. Infraestructura y Contenerización (Docker Compose)

Todo el ecosistema tecnológico se encuentra encapsulado en contenedores de **Docker**, lo que garantiza que el proyecto sea 100% portable y reproducible en cualquier entorno.

* **Orquestación Multi-Contenedor**: Mediante **Docker Compose**, se gestionan de forma simultánea los servicios de Airflow (Webserver, Scheduler, DB), la API de FastAPI y la interfaz de Streamlit.
* **Networking y Persistencia**: Se configuró una red interna para la comunicación segura entre microservicios y volúmenes compartidos para asegurar que los datos procesados por el pipeline estén disponibles para la aplicación.

[Ver informe completo de Integración](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/DOCKER-COMPOSE/README.md)

---

## 10. Cómo empezar (Instalación y Ejecución)

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
```

## Visualizaciones
* [Dashboard](https://drive.google.com/drive/folders/12x82i3Se9JESUq9tYNQd2I4xDhyfwusW)
* [Presentacion FashioDataInsights](https://docs.google.com/presentation/d/1ZW_UpRqZ-5Oa4zr0GJUk6pLlANSg_4UTBVDaGqmFuOI/edit?usp=sharing)

## Autores
Este es un proyecto desarrollado por:
* **Tobias Dagrava**: Estudiante de Ingeniería en Sistemas (UTN - FRLP), con especialización en Data Science y modelado de datos.
* **Samuel**: Desarrollador, colaborador y encargado de la gestión del repositorio y sincronización de datos.

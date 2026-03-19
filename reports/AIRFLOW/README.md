# Arquitectura de Datos y Orquestación

## 1. Infraestructura y Contenerización (Docker)
Para asegurar la reproducibilidad y el aislamiento del entorno de desarrollo, se implementó una arquitectura basada en **microservicios** utilizando **Docker** y **Docker Compose**.

* **Aislamiento de Entornos:** Se definieron contenedores independientes para los servicios críticos de orquestación:
    * **Airflow Webserver:** Interfaz gráfica para el monitoreo y gestión de tareas.
    * **Airflow Scheduler:** Motor encargado de lanzar las tareas según la programación definida.
    * **PostgreSQL:** Base de datos relacional dedicada a persistir los metadatos y estados de Airflow.
* **Gestión de Dependencias:** Se utilizó una imagen personalizada de Airflow que incluye el stack de Data Science necesario (`pandas`, `numpy`, `scikit-learn`, `scipy`), garantizando que el pipeline de datos corra en un entorno controlado y libre de conflictos de librerías locales.
* **Persistencia de Datos (Volumes):** Se configuraron volúmenes para mapear el directorio local `/data` con el sistema de archivos de los contenedores. Esto permite que los datasets (originales y procesados) persistan independientemente del ciclo de vida de los contenedores.

## 2. Orquestación del Pipeline (Apache Airflow)
La lógica del proyecto se estructuró mediante un **DAG (Directed Acyclic Graph)**, lo que permite una ejecución secuencial y modular de las tareas, facilitando la detección de errores en etapas tempranas.

### Etapas del Pipeline ETL:

1.  **Extracción (Extract):**
    * Carga automatizada de los datasets de **Fashion Data Insights**: transacciones, artículos y clientes.
    * Implementación de validaciones iniciales para asegurar la integridad de los archivos fuente antes del procesamiento.

2.  **Transformación (Transform):**
    * **Limpieza de Datos:** Identificación y tratamiento de valores nulos o inconsistentes en el historial de transacciones.
    * **Feature Engineering:** Procesamiento de variables para el sistema de recomendación (ej. cálculo de popularidad de artículos, segmentación de clientes por comportamiento de compra).
    * **Optimización:** Conversión de tipos de datos para reducir el consumo de memoria RAM durante la inferencia.

3.  **Carga (Load):**
    * Generación de archivos procesados en formato **Parquet**. Se eligió este formato por su eficiencia en almacenamiento columnar y velocidad de lectura para la posterior etapa de consumo en la API.

## 3. Ventajas de la Implementación
* **Trazabilidad:** Cada paso del proceso genera logs detallados, permitiendo identificar exactamente en qué punto falla una transformación.
* **Resiliencia:** Configuración de **Retries** automáticos para manejar fallos temporales de recursos.
* **Escalabilidad:** El diseño modular permite integrar nuevas fuentes de datos o modelos adicionales sin comprometer la lógica de negocio existente.
Load (Carga):

Exportación de la "Feature Store" resultante a un formato optimizado (Parquet) para que la API de FastAPI pueda consumirla con baja latencia.

3. Monitoreo y Escalabilidad
Al utilizar Airflow, el sistema gana capacidades de nivel empresarial:

Logs Detallados: Cada tarea genera un registro independiente, lo que facilita la depuración de errores en la fase de transformación.

Reintentos Automáticos (Retries): Configuración de políticas de reintento en caso de que una tarea falle por falta de memoria o recursos temporales.

Gantt Chart: Visualización de los tiempos de ejecución de cada tarea para identificar cuellos de botella en el procesamiento de los 6 millones de registros (o el volumen que maneje tu dataset).
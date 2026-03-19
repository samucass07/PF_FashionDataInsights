# Informe Técnico : Backend (FastAPI) e Interfaz (Streamlit)

## 1. Backend y Motor de Inferencia (FastAPI)
Para exponer el sistema de recomendación como un servicio escalable, se desarrolló un backend utilizando **FastAPI**. El objetivo es procesar las peticiones en tiempo real consultando los datos procesados por el pipeline de Airflow.

* **Dockerización del Servicio:** Se creó una imagen de Docker específica para el backend, garantizando que el entorno de ejecución sea independiente y ligero.
* **Gestión de Datos en Memoria:** La API consume los archivos **Parquet** generados en la etapa de ETL. Al utilizar este formato, se logra una carga de datos eficiente y rápida hacia los DataFrames de consulta.
* **Validación con Pydantic:** Se implementaron esquemas de datos para asegurar que las entradas (como el `customer_id`) cumplan con los formatos esperados, evitando errores de ejecución y mejorando la robustez de la API.
* **Documentación Interactiva:** Se habilitó el acceso a **/docs (Swagger UI)**, lo que permitió realizar pruebas de estrés y validación de los endpoints de recomendación de forma aislada antes de conectar el frontend.

## 2. Frontend e Interfaz de Usuario (Streamlit)
La interfaz se diseñó con **Streamlit** para ofrecer una experiencia de usuario (UX) fluida e intuitiva, permitiendo interactuar con los resultados del modelo sin necesidad de conocimientos técnicos.

* **Consumo de API:** El frontend actúa como un cliente desacoplado que se comunica con el backend mediante peticiones HTTP (librería `requests`). Esto permite que la interfaz sea rápida y que la lógica pesada quede delegada al servidor FastAPI.
* **Componentes de la Interfaz:**
    * **Buscador de Clientes:** Filtro dinámico para seleccionar IDs de usuarios y obtener recomendaciones personalizadas.
    * **Visualización de Artículos:** Renderización de los metadatos de los productos recomendados (nombre, categoría, precio).
    * **Análisis Exploratorio Integrado:** Incorporación de gráficos interactivos para mostrar tendencias de compra y distribución de artículos.
* **Despliegue Contenerizado:** Al igual que el resto del stack, Streamlit corre en su propio contenedor de Docker, facilitando el despliegue del ecosistema completo.

## 3. Comunicación y Flujo de Datos
La arquitectura asegura que la comunicación entre servicios sea eficiente y segura dentro de la red interna de Docker:

1.  El usuario solicita una recomendación en la UI de **Streamlit**.
2.  **Streamlit** envía una petición al endpoint de **FastAPI**.
3.  **FastAPI** consulta la "Feature Store" (archivos Parquet), ejecuta la lógica de recomendación y devuelve un JSON con los resultados.
4.  **Streamlit** recibe el JSON y formatea la salida visualmente para el usuario final.

## 4. Conclusiones Técnicas del Módulo
El desacoplamiento entre el backend y el frontend mediante esta arquitectura de microservicios permite una mayor mantenibilidad. Si se decide cambiar el motor de recomendación o actualizar la interfaz visual, cada componente puede modificarse de forma independiente sin afectar la estabilidad del sistema completo.
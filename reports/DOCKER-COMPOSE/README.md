# Integración y Orquestación con Docker Compose

## 1. Orquestación Multi-Contenedor
La pieza final de la arquitectura consiste en la integración de todos los servicios mediante **Docker Compose**. Esto permite levantar, configurar y conectar el ecosistema completo con un único comando, asegurando que el sistema sea 100% reproducible en cualquier servidor o entorno local.

* **Estandarización de Entornos:** Se definieron archivos `Dockerfile` específicos para cada servicio (Airflow, FastAPI y Streamlit), optimizando las imágenes para que contengan solo las dependencias estrictamente necesarias.
* **Dependencias de Inicio:** Se implementaron directivas `depends_on` para asegurar el orden correcto de ejecución (ej. que la base de datos de Airflow esté lista antes que el Scheduler).

## 2. Redes y Conectividad Interna (Networking)
Se configuró una red virtual interna de Docker para permitir la comunicación segura entre los componentes:

* **Aislamiento de Servicios:** Solo los contenedores que requieren interacción con el usuario (Streamlit y la documentación de FastAPI) tienen sus puertos expuestos al host.
* **Resolución de Nombres:** Los servicios se comunican entre sí utilizando sus nombres de contenedor (ej. `http://fastapi-service:8000`), lo que evita depender de direcciones IP locales volátiles.

## 3. Persistencia de Datos y Gestión de Volúmenes
Uno de los puntos críticos del diseño fue garantizar que los datos procesados no se pierdan al detener los contenedores.

* **Persistencia del Pipeline:** Se mapearon volúmenes para la carpeta `/data`, permitiendo que el archivo Parquet generado por el DAG de **Airflow** sea inmediatamente accesible por la API de **FastAPI**.
* **Base de Datos de Metadatos:** El volumen asociado a **PostgreSQL** asegura que el historial de ejecuciones y estados de las tareas de Airflow se mantenga íntegro tras reinicios del sistema.

## 4. Conclusión de la Arquitectura
La implementación final demuestra un flujo de **MLOps** simplificado pero robusto:

1.  **Orquestación:** Airflow gestiona el ciclo de vida de los datos.
2.  **Servicio:** FastAPI transforma los datos en inteligencia de negocio.
3.  **Interfaz:** Streamlit acerca esa inteligencia al usuario final.
4.  **Infraestructura:** Docker Compose garantiza que todo el conjunto sea portable, escalable y fácil de mantener.

Este diseño permite que el proyecto pase de una fase de desarrollo a una de pre-producción con cambios mínimos, cumpliendo con los estándares actuales de la industria en Ingeniería de Sistemas.
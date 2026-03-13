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

## 5. Modelo 1: Popularidad por Generación (Baseline)
El archivo `src/model_popularity_gen.py` contiene nuestro primer motor de recomendación, diseñado con arquitectura funcional de alto rendimiento:

* **In-Memory Processing**: Los datos se cargan en la RAM una sola vez, eliminando cuellos de botella.
* **Manejo de Cold Start**: "Fallback" seguro ofreciendo los productos más vendidos a nivel global de los últimos 90 días.
* **Regla de Negocio (Deduplicación)**: Implementa un filtro inteligente que evita recomendar el mismo modelo de prenda en distintos colores.

## 6. Cómo empezar (Instalación y Ejecución)

Si quieres replicar este proyecto, puedes ejecutar los siguientes comandos:

# Instalar las herramientas necesarias
!pip install pandas numpy

# Ejecutar el pipeline completo
!python src/etl.py
!python src/ft_engineering.py
!python src/model_popularity_gen.py

## Presentaciones
* [Presentación 1](https://github.com/samucass07/PF_FashionDataInsights/blob/main/reports/EDA/EDA.md)

## Autores
Este es un proyecto desarrollado por:
* **Tobias Dagrava**: Estudiante de Ingeniería en Sistemas (UTN - FRLP), con especialización en Data Science y modelado de datos.
* **Samuel**: Desarrollador, colaborador y encargado de la gestión del repositorio y sincronización de datos.
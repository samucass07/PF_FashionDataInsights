# H&M Fashion Recommendations - Data Engineering Pipeline

¡Bienvenido al repositorio central de nuestro proyecto de análisis de datos! Este trabajo es una colaboración conjunta diseñada para transformar datos crudos del sector retail en información estructurada y lista para modelos de Inteligencia Artificial.

## Autores
Este es un proyecto desarrollado por:
* **Tobias Dagrava**: Estudiante de Ingeniería en Sistemas (UTN - FRLP), con especialización en Data Science y modelado de datos.
* **Samuel**: Desarrollador colaborador y encargado de la gestión del repositorio y sincronización de datos.

---

## Estructura del Repositorio
Para que el proyecto sea fácil de navegar, hemos organizado las carpetas de la siguiente manera:

* **`data/`**: El almacén de datos.
    * **`raw/`**: Archivos originales descargados directamente de la fuente.
    * **`processed/`**: El resultado de nuestro trabajo; datos limpios y optimizados.
* **`notebooks/`**: Aquí realizamos el Análisis Exploratorio (EDA) para entender los datos antes de programar.
* **`src/`**: Contiene el motor del proyecto: `etl.py`.
* **`venv/`**: Nuestro entorno virtual para asegurar que las herramientas siempre funcionen correctamente.

---

## 1. El Corazón de los Datos (Dataset)
Trabajamos con tres pilares fundamentales de información proporcionados por H&M:

1.  **Clientes (`customers.csv`)**: Perfiles de **1.37 millones** de personas, incluyendo su edad y estado de membresía.
2.  **Artículos (`articles.csv`)**: Un catálogo de **105,542** prendas de vestir con detalles como color y tipo de producto.
3.  **Transacciones (`transactions_train.csv`)**: El registro masivo de más de **31 millones** de compras realizadas históricamente.

---

## 2. Análisis Exploratorio (EDA)
Antes de limpiar, realizamos una "revisión de salud" a los datos para detectar problemas:
* **Valores Faltantes**: Detectamos que muchos clientes no tenían registrada su edad y algunas prendas carecían de descripción detallada.
* **Formatos Mezclados**: Los códigos de los productos no siempre tenían el mismo formato, lo que dificultaba unirlos con las ventas.
* **Volumen Crítico**: Con 31 millones de filas, entendimos que necesitábamos técnicas especiales de programación para no colapsar la memoria de nuestras computadoras.



---

## 3. El Proceso de Limpieza (ETL)
El archivo `src/etl.py` es nuestra solución de ingeniería. Transforma los datos gigantes en archivos manejables en solo **1 minuto y 33 segundos**.

### ¿Qué hace exactamente este proceso?
* **Muestreo Inteligente**: Para que el desarrollo sea ágil, seleccionamos aleatoriamente al 10% de los clientes (aprox. 137,000) y mantenemos **todo** su historial de compras.
* **Imputación de Datos**: Completamos las edades faltantes usando la **mediana** (el valor central) para no distorsionar las estadísticas.
* **Optimización de RAM**: Cambiamos la forma en que la computadora lee los números para que ocupen un 60% menos de espacio en la memoria.
* **Integridad Referencial**: Nos aseguramos de que no existan compras de productos que no estén en el catálogo oficial.



[Image of data transformation pipeline]


---

## 4. Cómo empezar (Instalación)

Si quieres replicar este proyecto en tu computadora, sigue estos pasos:

1.  **Crea el entorno virtual (venv)**:
    ```bash
    python -m venv venv
    ```
2.  **Activa el entorno**:
    * En Windows: `.\venv\Scripts\activate`
    * En Mac/Linux: `source venv/bin/activate`
3.  **Instala las herramientas necesarias**:
    ```bash
    pip install pandas numpy
    ```
4.  **Ejecuta el proceso**:
    ```bash
    python src/etl.py
    ```


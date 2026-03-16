# Reporte de Feature Engineering (Ingeniería de Características)

## Objetivo de la Fase
El objetivo del Feature Engineering en este proyecto es transformar los datos transaccionales y demográficos limpios (provenientes de la fase ETL) en **variables predictivas**. Estas nuevas características están diseñadas específicamente para alimentar y optimizar los dos motores de recomendación principales: el modelo de Popularidad y el Filtrado Colaborativo.

---

## 1. Segmentación Demográfica 
La edad por sí sola es un número continuo que aporta poco valor a un recomendador de moda. Para extraer su verdadero potencial predictivo, transformamos esta variable en **Grupos Generacionales**. 

Se aplicó la siguiente lógica de discretización ("binning"):
* **Gen Z:** Menores de 25 años.
* **Millennials:** Entre 25 y 39 años.
* **Gen X:** Entre 40 y 54 años.
* **Seniors (Boomers+):** 55 años o más.

**Justificación de Negocio:** Las tendencias de moda varían drásticamente entre generaciones. Esta segmentación permite que el Modelo de Popularidad recomiende artículos específicos para el nicho generacional del cliente, en lugar de un *Best Seller* global genérico.

---

## 2. Análisis de Comportamiento (RFM) 
Para entender el valor y la actividad de cada usuario, implementamos un análisis RFM (Recency, Frequency, Monetary) adaptado al retail de moda:

* **Recencia (Recency):** Cantidad de días transcurridos desde la última compra del cliente. Permite identificar clientes activos vs. inactivos (dormant).
* **Frecuencia (Frequency):** Cantidad total de tickets o transacciones generadas.
* **Manejo de Cold Start:** Los clientes nuevos (sin historial transaccional en el set de entrenamiento) son identificados y etiquetados explícitamente. Esto es vital para que el orquestador híbrido sepa cuándo aplicar reglas de "salvavidas" (Popularidad Global).

---

## 3. Ventana de Tendencias (Decay Temporal) 
En la industria del *Fast Fashion*, un artículo que fue furor hace un año probablemente ya no esté en stock o haya pasado de moda. 

Para capturar la popularidad real, creamos características basadas en una **ventana de tiempo estricta de 90 días**.
* Se filtran todas las transacciones históricas y se conservan únicamente las de los últimos 3 meses respecto a la fecha máxima del dataset.
* Se calcula el volumen de ventas por artículo a nivel global y a nivel generacional dentro de este marco temporal.
* **Impacto:** Garantiza que el Baseline de Popularidad recomiende ropa de temporada (ej. abrigos en invierno, trajes de baño en verano).

---

## 4. Matriz de Interacciones (Reducción de Ruido) 
El Filtrado Colaborativo requiere una matriz de interacciones Usuario-Artículo. Sin embargo, procesar a todos los clientes genera matrices extremadamente dispersas y costosas computacionalmente.

**Regla de Filtrado:**
* Se generó un agrupamiento calculando cuántas veces un cliente compró un artículo específico.
* **Umbral de Calidad:** Se eliminaron los clientes "turistas" (aquellos con un historial de compras esporádico o casi nulo). Para formar parte de la matriz colaborativa, un cliente debe tener un historial sólido que permita inferir sus gustos.
* **Resultado:** Una reducción drástica en la dimensionalidad de la matriz, eliminando el "ruido" estadístico y mejorando el tiempo de procesamiento del cálculo de similitud del coseno en etapas posteriores.

---

## Artefactos Generados
Este pipeline consume los archivos de la carpeta `data/processed/` y genera los siguientes *datasets* enriquecidos, listos para el entrenamiento:

1. `features_customers.csv`: Perfiles de usuario enriquecidos con generación y métricas RFM.
2. `features_articles.csv`: Catálogo con banderas de popularidad y tendencias de 90 días.
3. `features_interactions.csv`: La base estructurada para la matriz dispersa del Filtro Colaborativo.
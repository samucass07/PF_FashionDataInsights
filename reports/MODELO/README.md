# Reporte de Modelos y Evaluación (Sistemas de Recomendación)

## Introducción
A diferencia de los problemas de Machine Learning tradicionales (Clasificación o Regresión), el objetivo de este proyecto es el **Ranking**. No buscamos predecir un valor exacto ni una etiqueta binaria (compró/no compró), sino generar una lista ordenada de los **12 artículos más relevantes** para cada cliente.

Para lograr esto, diseñamos una arquitectura competitiva: desarrollamos modelos con enfoques diametralmente opuestos, los optimizamos y los enfrentamos en un entorno de evaluación riguroso y libre de *Data Leakage*.

---

## 1. Prevención de Data Leakage
Antes de entrenar cualquier modelo, implementamos el script `train_test_split.py`. 
En el retail, el tiempo es una variable crítica. Por lo tanto, no podemos hacer un split aleatorio tradicional (dividir filas al azar), ya que el modelo podría "ver el futuro" para predecir el pasado.
* **Train:** Todas las transacciones históricas hasta la penúltima semana del dataset.
* **Test (Ground Truth):** Únicamente las transacciones de la **última semana**.
* **Resultado:** Los modelos entrenan a ciegas respecto a la última semana, simulando un entorno de producción real donde se debe predecir el comportamiento futuro.

---

## 2. Modelo 1: Popularidad Global (Baseline)
En la industria del *Fast Fashion*, el principio de Pareto (80/20) dicta que una pequeña fracción del catálogo genera la inmensa mayoría de las ventas. 

**Características técnicas (`model_popularity_gen.py`):**
* Agrupa las ventas de los últimos 90 días en la ventana de entrenamiento.
* **Ventaja:** Tiempo de inferencia casi instantáneo (O(1) mediante diccionarios en memoria) y cobertura absoluta (Cold Start = 0).
* **Desventaja:** Nulo nivel de personalización individual.

---

## 3. Modelo 2: Filtrado Colaborativo Basado en Usuarios


[Image of user-based collaborative filtering]

Para capturar compras de nicho, implementamos un algoritmo que recomienda artículos basándose en el historial de clientes con gustos similares ("vecinos").

**Características técnicas (`model_collaborative.py`):**
* **Optimización de Memoria:** Construcción de una *Sparse Matrix* (Matriz Dispersa) usando `scipy.sparse`, reduciendo el consumo de RAM para una matriz de más de 120,000 clientes x 85,000 artículos.
* **Cálculo de Similitud:** Similitud del Coseno entre vectores de compra.
* **Custom Grid Search (Ajuste de Hiperparámetros):** Se construyó un optimizador algorítmico automatizado para encontrar el número ideal de vecinos (`N_NEIGHBORS`). 
  * Se evaluó una grilla de `[20, 50, 100, 200, 300]`.
  * **Hallazgo:** El modelo encontró su pico de rendimiento en **200 vecinos**. Superar este umbral provocó que los gustos específicos se diluyeran en un "promedio", disminuyendo la precisión.

---

## 4. Orquestador Híbrido
El script `hybrid_recommender.py` ensambla los resultados de los modelos anteriores para mitigar sus debilidades individuales.
1. **Prioridad 1:** Inyecta las recomendaciones personalizadas del Modelo 2.
2. **Prioridad 2 (Padding & Cold Start):** Si el Modelo 2 no logra encontrar 12 artículos relevantes para un cliente, o si el cliente es completamente nuevo (Cold Start), el orquestador rellena los espacios vacíos utilizando los *Best Sellers* del Modelo 1.

---

## 5. El Evaluador Central y Métricas Avanzadas 
Se desarrolló un script independiente (`evaluate_models.py`) para auditar los resultados. Al tratar de un problema de Ranking con *Feedback Implícito* (solo sabemos qué compró el cliente, no qué ignoró), descartamos métricas como Accuracy o ROC-AUC y utilizamos el estándar de la industria:

* **MAP@12 (Mean Average Precision):** Evalúa la precisión promedio de las recomendaciones, priorizando los aciertos en los primeros lugares.
* **NDCG@12 (Normalized Discounted Cumulative Gain):** Métrica logarítmica que penaliza fuertemente si un artículo relevante es posicionado al final de la lista (ej: puesto 12) en lugar de al principio (ej: puesto 1).
* **Precision@12 y Recall@12:** Miden qué tan "limpia" es nuestra lista de 12 y qué porcentaje de la compra real del cliente logramos capturar, respectivamente.

---

## Resultados Finales y Conclusión de Negocio

A continuación, la tabla definitiva tras la evaluación de los 7,003 clientes activos en la semana de Test:

| Modelo | MAP@12 | NDCG@12 | Precision@12 | Recall@12 | Cobertura | Cold Start |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Popularidad** | **0.00380** | **0.00760** | **0.00303** | **0.01106** | **3.54%** | **0** |
| 2. Colaborativo (N=200)| 0.00262 | 0.00452 | 0.00167 | 0.00577 | 1.90% | 666 |
| 3. Híbrido | 0.00315 | 0.00543 | 0.00198 | 0.00702 | 2.27% | 0 |

### Conclusión Arquitectónica
Los datos empíricos demuestran que **el Modelo de Popularidad supera ampliamente a los algoritmos de filtrado complejo en este dataset.** Lejos de ser un fallo del Machine Learning, este resultado describe perfectamente el comportamiento del consumidor en el **Fast Fashion**:
1. Las compras son altamente impulsivas y están dictadas por macrotendencias de la temporada.
2. El catálogo rota con extrema rapidez (las prendas tienen una vida útil corta), lo que dificulta que el Filtro Colaborativo construya historiales profundos a largo plazo.

Por lo tanto, para un entorno de producción en este nicho específico, **el Modelo de Popularidad (Baseline) es la solución más eficiente**, ya que maximiza las métricas de negocio (NDCG/Recall) requiriendo una fracción del costo computacional. El híbrido, si bien rescata el Cold Start del Colaborativo, disminuye el rendimiento general al darle prioridad a recomendaciones de nicho sobre las tendencias masivas.
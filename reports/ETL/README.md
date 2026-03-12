# Preparación y Limpieza de Datos (Proceso ETL)
**Proyecto:** PF_FashionDataInsights

## 1. ¿Qué es este proceso y por qué es vital?
Antes de poder analizar qué compran nuestros clientes o crear un sistema que les recomiende ropa, necesitamos asegurarnos de que la información sea correcta, esté ordenada y no tenga errores. A este proceso de "purificación" lo llamamos ETL (Extracción, Transformación y Carga). Básicamente, es ordenar la casa y filtrar la información para que nuestro futuro sistema de recomendaciones funcione sobre cimientos sólidos.

## 2. Manejo Inteligente de Grandes Volúmenes (Eficiencia)
La base de datos original contiene decenas de millones de registros de compras. Procesar todo eso de golpe haría que cualquier sistema colapse o sea muy lento. 
* **Muestra Estratégica:** Seleccionamos un 10% de los clientes al azar y trabajamos con todo su historial. Esto nos permite tener una visión perfectamente representativa de la tienda, pero haciendo que nuestro sistema sea ágil, rápido y económico de ejecutar.
* **Optimización de Memoria:** Ajustamos la forma en la que el sistema lee los datos internamente. Al optimizar cómo guardamos números y categorías, logramos reducir drásticamente el peso de los archivos, acelerando los tiempos de carga y análisis.

## 3. Limpieza y Corrección de Errores
Los datos del mundo real siempre vienen con inconsistencias. En esta etapa aplicamos varias soluciones automatizadas:
* **Recuperación de Códigos de Producto:** Al leer los datos, muchos códigos de prendas perdían sus ceros a la izquierda, lo que impedía cruzar la ropa con su respectiva venta. Estandarizamos todos los códigos para que tengan exactamente 10 dígitos, recuperando información vital que de otro modo figuraría como "error".
* **Clientes sin Edad Registrada:** A los clientes que no declararon su edad al registrarse, se les asignó la edad media de nuestra base de datos. De esta forma, no los eliminamos y podemos seguir aprovechando su valioso historial de compras.
* **Textos Estandarizados:** Unificamos todos los textos (nombres de categorías, colores, etc.) a minúsculas y eliminamos espacios en blanco accidentales para que el sistema no confunda, por ejemplo, "Ladieswear" con "ladieswear".

## 4. Consistencia Total (Sin datos fantasma)
El paso final fue garantizar que la información cruce perfectamente entre sí, aplicando un filtro estricto de calidad:
* Eliminamos cualquier registro de compra de artículos que ya no existan en nuestro catálogo maestro.
* Filtramos a los clientes inactivos, quedándonos solo con aquellos que efectivamente realizaron al menos una compra en nuestra muestra.
* Ordenamos todo el historial de ventas cronológicamente. Esto es indispensable para que el futuro algoritmo entienda el "viaje del cliente" (qué compró primero y qué compró después).

## 5. El Resultado Final
Pasamos de tener archivos pesados, crudos y con ruido, a contar con tres tablas maestras (Clientes, Artículos y Transacciones) limpias y sincronizadas. Estos datos purificados son los que nos permitieron encontrar las tendencias de mercado recientes y son la materia prima exacta que usará nuestro modelo predictivo.

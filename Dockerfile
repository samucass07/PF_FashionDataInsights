# Usamos la imagen oficial de Apache Airflow como base
FROM apache/airflow:2.8.1-python3.10

# Copiamos nuestro archivo de dependencias al contenedor
COPY requirements.txt /

# Instalamos nuestras librerías de ML sobre la imagen de Airflow
RUN pip install --no-cache-dir -r /requirements.txt
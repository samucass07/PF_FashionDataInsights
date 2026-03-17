from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys

# Añadimos /opt/airflow/src al path para que Airflow encuentre tus scripts
sys.path.append('/opt/airflow/src')

# Importamos las funciones que refactorizamos antes
from etl import run_etl
from ft_engineering import run_feature_engineering
from train_test_split import run_train_test_split
from model_popularity_gen import run_popularity_model
from model_collaborative import run_collaborative_model
from hybrid_recommender import run_hybrid_model
from evaluate_models import run_evaluation

# Configuración básica del DAG
default_args = {
    'owner': 'tobias',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 16),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'fashion_recommendation_pipeline',
    default_args=default_args,
    description='Pipeline de Recomendación de Moda E2E',
    schedule_interval=None, # Lo corremos a mano por ahora
    catchup=False
) as dag:

    # Definición de las tareas (Tasks)
    task_etl = PythonOperator(task_id='etl_process', python_callable=run_etl)
    
    task_ft = PythonOperator(task_id='feature_engineering', python_callable=run_feature_engineering)
    
    task_split = PythonOperator(task_id='train_test_split', python_callable=run_train_test_split)
    
    task_model_pop = PythonOperator(task_id='model_popularity', python_callable=run_popularity_model)
    
    task_model_coll = PythonOperator(task_id='model_collaborative', python_callable=run_collaborative_model)
    
    task_hybrid = PythonOperator(task_id='hybrid_recommender', python_callable=run_hybrid_model)
    
    task_eval = PythonOperator(task_id='evaluate_all_models', python_callable=run_evaluation)

    # ─────────────────────────────────────────────
    # EL MAPA DE DEPENDENCIAS (El flujo)
    # ─────────────────────────────────────────────
    task_etl >> task_ft >> task_split
    task_split >> [task_model_pop, task_model_coll] >> task_hybrid
    task_hybrid >> task_eval
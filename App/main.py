from fastapi import FastAPI, HTTPException
import pandas as pd
import os

app = FastAPI(
    title="Fashion Recommendation API",
    description="API para servir recomendaciones de productos de moda (PF)",
    version="1.0.0"
)

# Ruta al archivo de recomendaciones generado por Airflow
# Usamos una ruta relativa que funcione tanto en local como en Docker
RECOMMENDATIONS_PATH = os.path.join("data", "processed", "recommendations_hybrid.csv")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Recomendaciones de Moda. Usa /docs para ver la documentación."}

@app.get("/recommend/{customer_id}")
def get_recommendations(customer_id: str):
    """
    Busca todas las filas para el customer_id y devuelve la lista de article_ids.
    """
    if not os.path.exists(RECOMMENDATIONS_PATH):
        raise HTTPException(status_code=500, detail="El archivo no existe.")

    try:
        df = pd.read_csv(RECOMMENDATIONS_PATH)
        
        # Filtramos todas las filas que coincidan con el cliente
        customer_data = df[df['customer_id'] == customer_id]
        
        if customer_data.empty:
            raise HTTPException(status_code=404, detail=f"No hay datos para el cliente {customer_id}")

        # Obtenemos todos los article_id de ese cliente y los pasamos a una lista
        # Usamos .astype(str) por si los IDs son numéricos, para que el JSON sea limpio
        predictions = customer_data['article_id'].astype(str).tolist()

        return {
            "customer_id": customer_id,
            "recommendations": predictions,
            "count": len(predictions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
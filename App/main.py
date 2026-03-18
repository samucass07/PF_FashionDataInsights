from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI(title="Fashion Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOMMENDATIONS_PATH = os.path.join(BASE_DIR, "data", "processed", "recommendations_hybrid.csv")
ARTICLES_PATH = os.path.join(BASE_DIR, "data", "processed", "articles_clean.csv")

# Cargamos el catálogo de artículos al inicio
if os.path.exists(ARTICLES_PATH):
    df_articles = pd.read_csv(ARTICLES_PATH)
    # Forzamos article_id a string para evitar problemas de tipos
    df_articles['article_id'] = df_articles['article_id'].astype(str)
else:
    df_articles = None

@app.get("/")
def read_root():
    return {"message": "API activa. Ve a /docs para probarla."}

@app.get("/recommend/{customer_id}")
def get_recommendations(customer_id: str):
    if not os.path.exists(RECOMMENDATIONS_PATH):
        raise HTTPException(status_code=500, detail="Archivo de recomendaciones no encontrado")

    try:
        df_recs = pd.read_csv(RECOMMENDATIONS_PATH)
        customer_recs = df_recs[df_recs['customer_id'] == customer_id]
        
        if customer_recs.empty:
            raise HTTPException(status_code=404, detail=f"No hay recomendaciones para el cliente {customer_id}")

        ids = customer_recs['article_id'].astype(str).tolist()
        result = []

        for aid in ids:
            # Info por defecto si no lo encuentra en el catálogo
            item_info = {
                "article_id": aid, 
                "name": "Producto desconocido", 
                "category": "N/A", 
                "color": "N/A"
            }
            
            if df_articles is not None:
                row = df_articles[df_articles['article_id'] == aid]
                if not row.empty:
                    item_info["name"] = row.iloc[0]['prod_name']
                    item_info["category"] = row.iloc[0]['product_type_name']
                    item_info["color"] = row.iloc[0]['colour_group_name']
            
            result.append(item_info)

        return {"customer_id": customer_id, "recommendations": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
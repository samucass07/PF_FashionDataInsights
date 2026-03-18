import streamlit as st
import requests
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Fashion Advisor PF", layout="wide")

st.title("👗 Fashion Recommendation System")
st.markdown("Introduce tu ID de cliente para obtener las mejores ofertas personalizadas.")

# Input del Customer ID
customer_id = st.text_input("Customer ID", placeholder="Pega aquí el ID del cliente...")

if st.button("Obtener Recomendaciones"):
    if customer_id:
        with st.spinner('Consultando al cerebro de la IA...'):
            try:
                # Llamamos a nuestra API de FastAPI
                response = requests.get(f"http://127.0.0.1:8000/recommend/{customer_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    recs = data['recommendations']
                    
                    st.success(f"¡Listo! Encontramos recomendaciones para el cliente:")
                    
                    # Convertimos a DataFrame para mostrarlo lindo
                    df_display = pd.DataFrame(recs)
                    
                    # Renombramos columnas para el usuario
                    df_display.columns = ["ID Artículo", "Producto", "Categoría", "Color"]
                    
                    # Mostramos la tabla que ocupa todo el ancho
                    st.dataframe(df_display, use_container_width=True)
                else:
                    error_msg = response.json().get('detail', 'Error desconocido')
                    st.error(f"Error de la API: {error_msg}")
            except Exception as e:
                st.error(f"No se pudo conectar con la API. Asegúrate de que el comando 'uvicorn' esté corriendo. Error: {e}")
    else:
        st.warning("Por favor, ingresa un ID de cliente.")
import streamlit as st
import requests
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Fashion Advisor PF", layout="centered")

st.title("👗 Fashion Recommendation System")
st.markdown("Introduce tu ID de cliente para obtener las mejores ofertas personalizadas.")

# Input del Customer ID
customer_id = st.text_input("Customer ID", placeholder="Pega aquí el ID del cliente...")

if st.button("Obtener Recomendaciones"):
    if customer_id:
        with st.spinner('Consultando al cerebro de la IA...'):
            try:
                # Llamamos a nuestra API de FastAPI
                # Si estás en local es 127.0.0.1, si estás en Docker será 'api'
                response = requests.get(f"http://127.0.0.1:8000/recommend/{customer_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    recs = data['recommendations']
                    
                    st.success(f"¡Listo! Encontramos {data['count']} recomendaciones:")
                    
                    # Mostramos los IDs en una tabla linda
                    df_recs = pd.DataFrame(recs, columns=["Article ID"])
                    st.table(df_recs)
                else:
                    st.error(f"Error: {response.json().get('detail', 'No encontrado')}")
            except Exception as e:
                st.error(f"No se pudo conectar con la API. ¿Está prendida? Error: {e}")
    else:
        st.warning("Por favor, ingresa un ID.")
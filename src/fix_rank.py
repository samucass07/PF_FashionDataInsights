"""
Agrega columna rank correcta a recommendations_model1.csv
Corre esto una sola vez y reemplaza el CSV.
"""
import pandas as pd
from config import PROCESSED_DIR

recs = pd.read_csv(PROCESSED_DIR / "recommendations_model1.csv", dtype={'customer_id': str, 'article_id': str})

# Rank que reinicia en 1 para cada cliente
recs["rank"] = recs.groupby("customer_id").cumcount() + 1

recs.to_csv(PROCESSED_DIR / "recommendations_model1.csv", index=False)
print(f"Listo. {len(recs):,} filas guardadas con rank 1-12 por cliente.")
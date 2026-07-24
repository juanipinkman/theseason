import pandas as pd

# Leer el historial actual del CSV
df = pd.read_csv("data/db1_historial.csv")

# Guardar solo las columnas que vamos a editar manualmente
df_limpio = df[["temporada", "equipo", "division", "posicion", "pts_tabla"]].copy()
df_limpio = df_limpio.sort_values(["temporada", "division", "posicion"]).reset_index(drop=True)

df_limpio.to_excel("data/db1_historial.xlsx", index=False)
print(f"Excel creado con {len(df_limpio)} registros.")
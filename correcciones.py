import pandas as pd

correcciones = [
    {"temporada": "2018/19", "equipo": "Brentford", "division": "Championship", "posicion": 11, "pts_tabla": 64},
]

df = pd.DataFrame(correcciones)
df.to_csv("data/correcciones.csv", index=False, encoding="utf-8")
print(f"{len(df)} correcciones guardadas en data/correcciones.csv")
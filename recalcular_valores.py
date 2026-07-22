import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))
from config import DIVISION_POINTS, MODIFIERS

DIVISION_FACTORS = {
    "Premier League": 1.0,
    "Championship": 0.7,
    "League One": 0.45,
    "League Two": 0.25,
    "National League": 0.15,
    "National League North": 0.08,
    "National League South": 0.08,
    "Northern Premier Division": 0.04,
    "Southern League Premier Central": 0.04,
    "Southern League Premier South": 0.04,
    "Isthmian League Premier Division": 0.04,
}

def detect_modifiers(position, total_teams, division_name, base_points):
    mods = []
    total_points = 0

    if position == 1:
        mods.append("campeon")
        total_points += round(base_points * 0.20, 1)

    ascenso_directo = {
        "Championship": [2], "League One": [2], "League Two": [2, 3],
        "National League": [2], "National League North": [2], "National League South": [2],
        "Northern Premier Division": [2], "Southern League Premier Central": [2],
        "Southern League Premier South": [2], "Isthmian League Premier Division": [2],
    }
    if division_name in ascenso_directo and position in ascenso_directo[division_name]:
        mods.append("ascenso_directo")
        total_points += round(base_points * 0.10, 1)

    playoff_positions = {
        "Championship": [3,4,5,6], "League One": [3,4,5,6], "League Two": [4,5,6,7],
        "National League": [3,4,5,6], "National League North": [3,4,5,6],
        "National League South": [3,4,5,6], "Northern Premier Division": [3,4,5,6],
        "Southern League Premier Central": [3,4,5,6], "Southern League Premier South": [3,4,5,6],
        "Isthmian League Premier Division": [3,4,5,6],
    }
    if division_name in playoff_positions and position in playoff_positions[division_name]:
        mods.append("playoff_sin_ascenso")
        total_points += round(base_points * 0.03, 1)

    descenso_positions = {
        "Premier League": list(range(total_teams - 2, total_teams + 1)),
        "Championship": list(range(total_teams - 2, total_teams + 1)),
        "League One": list(range(total_teams - 3, total_teams + 1)),
        "League Two": list(range(total_teams - 1, total_teams + 1)),
        "National League": list(range(total_teams - 2, total_teams + 1)),
        "National League North": list(range(total_teams - 2, total_teams + 1)),
        "National League South": list(range(total_teams - 2, total_teams + 1)),
        "Northern Premier Division": list(range(total_teams - 2, total_teams + 1)),
        "Southern League Premier Central": list(range(total_teams - 2, total_teams + 1)),
        "Southern League Premier South": list(range(total_teams - 2, total_teams + 1)),
        "Isthmian League Premier Division": list(range(total_teams - 2, total_teams + 1)),
    }
    if division_name in descenso_positions and position in descenso_positions[division_name]:
        mods.append("descenso")
        total_points -= round(base_points * 0.15, 1)

    if position == total_teams:
        mods.append("ultimo_lugar")
        total_points -= round(base_points * 0.10, 1)

    return mods, round(total_points, 1)

print("Cargando historial...")
df = pd.read_csv("data/db1_historial.csv")

print("Recalculando valores...")
nuevos_registros = []
for _, row in df.iterrows():
    division_name = row["division"]
    base_points = DIVISION_POINTS.get(division_name, 0)
    factor = DIVISION_FACTORS.get(division_name, 1.0)
    pts_tabla = row["pts_tabla"]
    pts_ponderados = round(pts_tabla * factor, 1)
    position = int(row["posicion"])

    total_teams = df[(df["temporada"] == row["temporada"]) & (df["division"] == division_name)]["posicion"].max()

    mods, mod_points = detect_modifiers(position, total_teams, division_name, base_points)
    year_value = round(base_points + pts_ponderados + mod_points, 1)

    nuevos_registros.append({
        **row.to_dict(),
        "pts_ponderados": pts_ponderados,
        "factor_division": factor,
        "modificadores": ", ".join(mods) if mods else "-",
        "puntos_modificadores": mod_points,
        "valor_temporada": year_value,
    })

df_nuevo = pd.DataFrame(nuevos_registros)

avg_df = df_nuevo.groupby("equipo").agg(
    valor_promedio=("valor_temporada", "mean"),
    temporadas_jugadas=("temporada", "count"),
    promedio_pts_tabla=("pts_tabla", "mean"),
).round(1).reset_index()
avg_df = avg_df.sort_values("valor_promedio", ascending=False)

df_nuevo.to_csv("data/db1_historial.csv", index=False, encoding="utf-8")
avg_df.to_csv("data/db1_valores.csv", index=False, encoding="utf-8")

print("\nListo.")
print(f"  Registros: {len(df_nuevo)}")
print(f"  Equipos unicos: {len(avg_df)}")
print("\nTop 10:")
print(avg_df.head(10).to_string(index=False))
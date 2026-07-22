import pandas as pd

ORDEN_DIVISIONES = [
    "Premier League",
    "Championship",
    "League One",
    "League Two",
    "National League",
    "National League North",
    "National League South",
    "Northern Premier Division",
    "Southern League Premier Central",
    "Southern League Premier South",
    "Isthmian League Premier Division",
]

def division_arriba(div):
    idx = ORDEN_DIVISIONES.index(div) if div in ORDEN_DIVISIONES else -1
    return ORDEN_DIVISIONES[idx - 1] if idx > 0 else div

def division_abajo(div):
    idx = ORDEN_DIVISIONES.index(div) if div in ORDEN_DIVISIONES else -1
    return ORDEN_DIVISIONES[idx + 1] if idx < len(ORDEN_DIVISIONES) - 1 else div

df = pd.read_csv("data/db1_historial.csv")
ultima_temp = df["temporada"].sort_values().iloc[-1]
print(f"Calculando división actual desde temporada {ultima_temp}...")

df_ultima = df[df["temporada"] == ultima_temp].copy()

resultados = []
for _, row in df_ultima.iterrows():
    equipo = row["equipo"]
    division = row["division"]
    mods = row["modificadores"]

    if any(m in mods for m in ["campeon", "ascenso_directo", "playoff_ascenso"]):
        division_actual = division_arriba(division)
        movimiento = "↑ ascenso"
    elif "descenso" in mods:
        division_actual = division_abajo(division)
        movimiento = "↓ descenso"
    else:
        division_actual = division
        movimiento = "= sin cambio"

    resultados.append({
        "equipo": equipo,
        "division_25_26": division,
        "modificadores": mods,
        "movimiento": movimiento,
        "division_actual": division_actual,
    })

df_result = pd.DataFrame(resultados)
df_result.to_csv("data/division_actual.csv", index=False, encoding="utf-8")

print(f"\nListo. {len(df_result)} equipos procesados.")
print(f"\nEquipos con cambio de división:")
cambios = df_result[df_result["movimiento"] != "= sin cambio"]
print(cambios[["equipo", "division_25_26", "movimiento", "division_actual"]].to_string(index=False))
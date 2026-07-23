import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import sys
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))
from config import DIVISION_POINTS, MODIFIERS

HEADERS = {"User-Agent": "Mozilla/5.0"}

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

def get_standings_wikipedia(url):
    anchor = None
    if '#' in url:
        url_clean, anchor = url.split('#', 1)
    else:
        url_clean = url

    try:
        r = requests.get(url_clean, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"    Error {r.status_code} - {url_clean}")
            return None
    except Exception as e:
        print(f"    Excepcion: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    if anchor:
        anchor_tag = soup.find(id=anchor)
        if not anchor_tag:
            anchor_tag = soup.find("span", {"id": anchor})
        if anchor_tag:
            anchor_tag = anchor_tag.find_parent(["h2", "h3", "h4"]) or anchor_tag
        if not anchor_tag:
            anchor_clean = anchor.replace('_', ' ')
            anchor_tag = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and anchor_clean.lower() in tag.get_text().lower())
        if anchor_tag:
            anchor_level = anchor_tag.name
            for sibling in anchor_tag.find_all_next():
                if sibling.name == anchor_level and sibling.get('id') != anchor:
                    break
                if sibling.name == 'table' and 'wikitable' in sibling.get('class', []):
                    result = extract_teams_from_table(sibling)
                    if result:
                        return result
        print(f"    No se encontro anchor '{anchor}'")
        return None
    else:
        tables = soup.find_all("table", {"class": "wikitable"})
        for table in tables:
            result = extract_teams_from_table(table)
            if result:
                return result
        print(f"    No se encontro tabla en {url_clean}")
        return None

def extract_teams_from_table(table):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if "Pos" not in headers or not any("Team" in h for h in headers):
        return None

    pos_idx = headers.index("Pos")
    team_idx = next(i for i, h in enumerate(headers) if "Team" in h)
    pts_idx = headers.index("Pts") if "Pts" in headers else None

    rows = table.find_all("tr")[1:]
    standings = []
    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 3:
            continue
        try:
            pos = int(cols[pos_idx].get_text(strip=True))
            team = cols[team_idx].get_text(strip=True)
            team = re.sub(r'\s*\(.*?\)', '', team).strip()
            team = re.sub(r'\s*\[.*?\]', '', team).strip()
            pts = int(cols[pts_idx].get_text(strip=True)) if pts_idx is not None else 0
            standings.append({"position": pos, "team": team, "pts": pts})
        except (ValueError, IndexError):
            continue

    return standings if standings else None

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

def build_db1():
    print("Iniciando construccion de DB1 desde Wikipedia...")
    all_records = []

    urls_df = pd.read_excel("config/urls_scrapeo.xlsx")
    urls_df = urls_df[urls_df["activo"] == 1]
    total = len(urls_df)

    for i, row in urls_df.iterrows():
        season_str = row["temporada"]
        division_name = row["division"]
        url = row["url"]

        print(f"  [{i+1}/{total}] {season_str} — {division_name}...")
        standings = get_standings_wikipedia(url)

        if not standings:
            continue

        total_teams = len(standings)
        base_points = DIVISION_POINTS.get(division_name, 0)
        factor = DIVISION_FACTORS.get(division_name, 1.0)

        if base_points == 0:
            print(f"    Sin puntos base para {division_name}, saltando...")
            continue

        for entry in standings:
            position = entry["position"]
            team_name = entry["team"]
            pts_tabla = entry["pts"]
            pts_ponderados = round(pts_tabla * factor, 1)

            mods, mod_points = detect_modifiers(position, total_teams, division_name, base_points)
            year_value = round(base_points + pts_ponderados + mod_points, 1)

            all_records.append({
                "temporada": season_str,
                "equipo": team_name,
                "division": division_name,
                "posicion": position,
                "pts_tabla": pts_tabla,
                "factor_division": factor,
                "pts_ponderados": pts_ponderados,
                "modificadores": ", ".join(mods) if mods else "-",
                "puntos_base": base_points,
                "puntos_modificadores": mod_points,
                "valor_temporada": year_value,
            })

        time.sleep(1)

    if not all_records:
        print("\nNo se obtuvieron datos.")
        return

    df = pd.DataFrame(all_records)

    avg_df = df.groupby("equipo").agg(
        valor_promedio=("valor_temporada", "mean"),
        temporadas_jugadas=("temporada", "count"),
        promedio_pts_tabla=("pts_tabla", "mean"),
    ).round(1).reset_index()

    avg_df = avg_df.sort_values("valor_promedio", ascending=False)

    os.makedirs("data", exist_ok=True)
    # No sobreescribir — solo agregar temporadas nuevas
if os.path.exists("data/db1_historial.csv"):
    df_existente = pd.read_csv("data/db1_historial.csv")
    temporadas_existentes = set(df_existente["temporada"].unique())
    temporadas_nuevas = set(df["temporada"].unique())
    temporadas_a_agregar = temporadas_nuevas - temporadas_existentes
    
    if not temporadas_a_agregar:
        print("\nNo hay temporadas nuevas para agregar.")
        return
    
    df_nuevo = df[df["temporada"].isin(temporadas_a_agregar)]
    df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    df_final = df_final.sort_values(["temporada", "division", "posicion"]).reset_index(drop=True)
    df_final.to_csv("data/db1_historial.csv", index=False, encoding="utf-8")
    print(f"\nAgregadas temporadas: {temporadas_a_agregar}")
    print(f"Total registros: {len(df_final)}")
else:
    df.to_csv("data/db1_historial.csv", index=False, encoding="utf-8")
    print(f"\nHistorial creado con {len(df)} registros.")
    avg_df.to_csv("data/db1_valores.csv", index=False, encoding="utf-8")

    print("\nListo.")
    print(f"  Registros historicos: {len(df)}")
    print(f"  Equipos unicos: {len(avg_df)}")
    print(f"  Archivos guardados en data/")
    print("\nTop 10 equipos por valor promedio:")
    print(avg_df.head(10).to_string(index=False))

if __name__ == "__main__":
    build_db1()
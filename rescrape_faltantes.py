import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))
from config import DIVISION_POINTS

HEADERS = {"User-Agent": "Mozilla/5.0"}

FALTANTES = [
    {"temporada": "2022/23", "division": "National League"},
    {"temporada": "2022/23", "division": "National League South"},
    {"temporada": "2022/23", "division": "Northern Premier Division"},
    {"temporada": "2022/23", "division": "Southern League Premier Central"},
    {"temporada": "2023/24", "division": "League One"},
    {"temporada": "2023/24", "division": "League Two"},
    {"temporada": "2023/24", "division": "National League"},
    {"temporada": "2023/24", "division": "National League South"},
    {"temporada": "2023/24", "division": "Northern Premier Division"},
    {"temporada": "2024/25", "division": "Championship"},
    {"temporada": "2024/25", "division": "Isthmian League Premier Division"},
    {"temporada": "2024/25", "division": "Northern Premier Division"},
    {"temporada": "2025/26", "division": "Championship"},
    {"temporada": "2025/26", "division": "Northern Premier Division"},
]

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

def get_standings(url):
    anchor = None
    if '#' in url:
        url_clean, anchor = url.split('#', 1)
    else:
        url_clean = url
    try:
        r = requests.get(url_clean, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"    Error {r.status_code}")
            return None
    except Exception as e:
        print(f"    Excepcion: {e}")
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    if anchor:
        anchor_tag = soup.find(id=anchor)
        if anchor_tag:
            anchor_level = anchor_tag.name
            for sibling in anchor_tag.find_all_next():
                if sibling.name == anchor_level and sibling.get('id') != anchor:
                    break
                if sibling.name == 'table' and 'wikitable' in sibling.get('class', []):
                    result = extract_teams_from_table(sibling)
                    if result:
                        return result
    else:
        for table in soup.find_all("table", {"class": "wikitable"}):
            result = extract_teams_from_table(table)
            if result:
                return result
    return None

# Cargar URLs del Excel
urls_df = pd.read_excel("config/urls_scrapeo.xlsx")
urls_df = urls_df[urls_df["activo"] == 1]

# Cargar historial existente
df = pd.read_csv("data/db1_historial.csv")
nuevos = []

for item in FALTANTES:
    temporada = item["temporada"]
    division = item["division"]
    season_year = temporada.split("/")[0]
    
    # Buscar URL en el Excel
    mask = (urls_df["temporada"] == temporada) & (urls_df["division"] == division)
    if not mask.any():
        print(f"  Sin URL: {temporada} {division}")
        continue
    
    url = urls_df[mask]["url"].values[0]
    print(f"  {temporada} — {division}...")
    
    standings = get_standings(url)
    if not standings:
        print(f"    Sin datos")
        continue

    # Eliminar registros existentes de esa temporada/división
    df = df[~((df["temporada"] == temporada) & (df["division"] == division))]

    for entry in standings:
        nuevos.append({
            "temporada": temporada,
            "equipo": entry["team"],
            "division": division,
            "posicion": entry["position"],
            "pts_tabla": entry["pts"],
            "factor_division": 0,
            "pts_ponderados": 0,
            "modificadores": "-",
            "puntos_base": DIVISION_POINTS.get(division, 0),
            "puntos_modificadores": 0,
            "valor_temporada": 0,
        })
    
    print(f"    {len(standings)} equipos")
    time.sleep(1)

if nuevos:
    df = pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True)
    df = df.sort_values(["temporada", "division", "posicion"]).reset_index(drop=True)
    df.to_csv("data/db1_historial.csv", index=False, encoding="utf-8")
    print(f"\nListo. {len(nuevos)} registros nuevos agregados.")
else:
    print("\nNo se agregaron registros.")
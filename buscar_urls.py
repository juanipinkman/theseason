import requests
import pandas as pd
import time
import re
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
HEADERS = {"User-Agent": "Mozilla/5.0"}

SEARCH_TEMPLATES = {
    "National League": [
        "https://en.wikipedia.org/wiki/{sd}_National_League_(football)",
        "https://en.wikipedia.org/wiki/{sd}_National_League_(English_football)",
        "https://en.wikipedia.org/wiki/{sd}_Conference_National",
    ],
    "National League North": [
        "https://en.wikipedia.org/wiki/{sd}_National_League_North",
        "https://en.wikipedia.org/wiki/{sd}_Conference_North",
    ],
    "National League South": [
        "https://en.wikipedia.org/wiki/{sd}_National_League_South",
        "https://en.wikipedia.org/wiki/{sd}_Conference_South",
    ],
    "Northern Premier Division": [
        "https://en.wikipedia.org/wiki/{sd}_Northern_Premier_League_Premier_Division",
        "https://en.wikipedia.org/wiki/{sd}_Northern_Premier_League",
    ],
    "Southern League Premier Central": [
        "https://en.wikipedia.org/wiki/{sd}_Southern_Football_League_Premier_Division_Central",
        "https://en.wikipedia.org/wiki/{sd}_Southern_League_Premier_Division_Central",
        "https://en.wikipedia.org/wiki/{sd}_Southern_Football_League",
    ],
    "Southern League Premier South": [
        "https://en.wikipedia.org/wiki/{sd}_Southern_Football_League_Premier_Division_South",
        "https://en.wikipedia.org/wiki/{sd}_Southern_League_Premier_Division_South",
    ],
    "Isthmian League Premier Division": [
        "https://en.wikipedia.org/wiki/{sd}_Isthmian_League_Premier_Division",
        "https://en.wikipedia.org/wiki/{sd}_Isthmian_League",
    ],
}

def probar_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.status_code == 200
    except:
        return False

def encontrar_url(division, season_dash):
    templates = SEARCH_TEMPLATES.get(division, [])
    for template in templates:
        url = template.format(sd=season_dash)
        if probar_url(url):
            return url
        time.sleep(0.3)
    return None

df = pd.read_excel("config/urls_scrapeo.xlsx")

divisiones_a_buscar = list(SEARCH_TEMPLATES.keys())
mask = df["division"].isin(divisiones_a_buscar)
filas = df[mask]

print(f"Buscando URLs correctas para {len(filas)} combinaciones...\n")

for i, row in filas.iterrows():
    season_dash = row["temporada"].replace("/", "-")
    division = row["division"]
    print(f"  {row['temporada']} — {division}...")
    
    url = encontrar_url(division, season_dash)
    if url:
        df.at[i, "url"] = url
        df.at[i, "activo"] = 1
        print(f"    ✓ {url}")
    else:
        df.at[i, "activo"] = 0
        print(f"    ✗ No encontrada")
    
    time.sleep(0.5)

df.to_excel("config/urls_scrapeo.xlsx", index=False)

activas = df["activo"].sum()
inactivas = len(df) - activas
print(f"\nListo. {activas} URLs activas, {inactivas} sin encontrar.")
print("Excel actualizado en config/urls_scrapeo.xlsx")
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import os

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_teams_from_url(url):
    anchor = None
    if '#' in url:
        url_clean, anchor = url.split('#', 1)
    else:
        url_clean = url

    try:
        r = requests.get(url_clean, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"    Error {r.status_code} - {url_clean}")
            return []
    except Exception as e:
        print(f"    Excepcion: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    if anchor:
        anchor_tag = soup.find(id=anchor)
        if not anchor_tag:
            print(f"    Anchor '{anchor}' no encontrado")
            return []

        # Buscar todas las wikitables entre este heading y el siguiente del mismo nivel
        anchor_level = anchor_tag.name
        tables_found = []
        for sibling in anchor_tag.find_all_next():
            if sibling.name == anchor_level and sibling.get('id') != anchor:
                break
            if sibling.name == 'table' and 'wikitable' in sibling.get('class', []):
                teams = extract_teams_from_table(sibling)
                if teams:
                    return teams

        print(f"    No se encontro tabla valida para anchor '{anchor}'")
        return []
    else:
        tables = soup.find_all("table", {"class": "wikitable"})
        for table in tables:
            teams = extract_teams_from_table(table)
            if teams:
                return teams
        print(f"    No se encontro tabla en {url_clean}")
        return []

def extract_teams_from_table(table):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if "Pos" not in headers or not any("Team" in h for h in headers):
        return []
    
    team_idx = next(i for i, h in enumerate(headers) if "Team" in h)
    rows = table.find_all("tr")[1:]
    teams = []
    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        try:
            int(cols[0].get_text(strip=True))
            team = cols[team_idx].get_text(strip=True)
            team = re.sub(r'\s*\(.*?\)', '', team).strip()
            team = re.sub(r'\s*\[.*?\]', '', team).strip()
            if team:
                teams.append(team)
        except ValueError:
            continue
    return teams

print("Scrapeando division actual (26/27)...")
urls_df = pd.read_excel("config/urls_scrapeo.xlsx")
urls_26 = urls_df[urls_df["activo"] == 2]

registros = []
for _, row in urls_26.iterrows():
    division = row["division"]
    url = row["url"]
    print(f"  {division}...")
    teams = get_teams_from_url(url)
    print(f"    {len(teams)} equipos encontrados")
    for team in teams:
        registros.append({"equipo": team, "division_actual": division})

df = pd.DataFrame(registros)
os.makedirs("data", exist_ok=True)
df.to_csv("data/division_actual.csv", index=False, encoding="utf-8")

print(f"\nListo. {len(df)} equipos en division_actual.csv")
print(df["division_actual"].value_counts().to_string())
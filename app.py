import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template

app = Flask(__name__)

API_KEY = "ca6a99f3f0da4397a9fc9a31c5e0e4a9"

# ── Fuentes de datos ────────────────────────────────────────────────────────
# football-data.org (plan free): PL y Championship
API_LIGAS = {"PL", "ELC"}

# BBC Sport (scraping): League One → National League South
# footballwebpages.co.uk usa Cloudflare managed-challenge (no bypasseable sin browser real)
BBC_LIGAS = {
    "EL1": "https://www.bbc.com/sport/football/league-one/table",
    "EL2": "https://www.bbc.com/sport/football/league-two/table",
    "NL":  "https://www.bbc.com/sport/football/national-league/table",
    "NLN": "https://www.bbc.com/sport/football/national-league-north/table",
    "NLS": "https://www.bbc.com/sport/football/national-league-south/table",
}

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

# ── Jugadores ───────────────────────────────────────────────────────────────
jugadores = [
    {
        "nombre": "Guillote",
        "equipos": [
            {"liga": "Premier League",        "codigo": "PL",  "nombre": "Chelsea FC",                "id": 61},
            {"liga": "Championship",           "codigo": "ELC", "nombre": "Charlton Athletic FC",      "id": 348},
            {"liga": "League One",             "codigo": "EL1", "nombre": "Plymouth Argyle FC",        "id": None},
            {"liga": "League Two",             "codigo": "EL2", "nombre": "Notts County FC",           "id": None},
            {"liga": "National League",        "codigo": "NL",  "nombre": "York City FC",              "id": None},
            {"liga": "National League North",  "codigo": "NLN", "nombre": "Kidderminster Harriers FC", "id": None},
            {"liga": "National League South",  "codigo": "NLS", "nombre": "Torquay United FC",         "id": None},
        ],
    },
    {
        "nombre": "JM",
        "equipos": [
            {"liga": "Premier League",        "codigo": "PL",  "nombre": "Liverpool FC",                   "id": 64},
            {"liga": "Championship",           "codigo": "ELC", "nombre": "Wrexham AFC",                    "id": 404},
            {"liga": "League One",             "codigo": "EL1", "nombre": "Wigan Athletic FC",              "id": None},
            {"liga": "League Two",             "codigo": "EL2", "nombre": "Barrow AFC",                     "id": None},
            {"liga": "National League",        "codigo": "NL",  "nombre": "Boston United FC",               "id": None},
            {"liga": "National League North",  "codigo": "NLN", "nombre": "Hereford FC",                    "id": None},
            {"liga": "National League South",  "codigo": "NLS", "nombre": "Hampton & Richmond Borough FC",  "id": None},
        ],
    },
    {
        "nombre": "Laionel",
        "equipos": [
            {"liga": "Premier League",        "codigo": "PL",  "nombre": "Manchester United FC",  "id": 66},
            {"liga": "Championship",           "codigo": "ELC", "nombre": "Leicester City FC",     "id": 338},
            {"liga": "League One",             "codigo": "EL1", "nombre": "AFC Wimbledon",         "id": None},
            {"liga": "League Two",             "codigo": "EL2", "nombre": "Oldham Athletic AFC",   "id": None},
            {"liga": "National League",        "codigo": "NL",  "nombre": "Carlisle United FC",    "id": None},
            {"liga": "National League North",  "codigo": "NLN", "nombre": "Chester FC",            "id": None},
            {"liga": "National League South",  "codigo": "NLS", "nombre": "Maidstone United FC",  "id": None},
        ],
    },
]


# ── Data fetching ────────────────────────────────────────────────────────────

def obtener_datos_liga(codigo):
    """football-data.org → {nombre_equipo: {puntos, pj, escudo}} | None si falla."""
    try:
        r = requests.get(
            f"https://api.football-data.org/v4/competitions/{codigo}/standings",
            headers={"X-Auth-Token": API_KEY},
        )
        r.raise_for_status()
        datos = {}
        for entrada in r.json()["standings"][0]["table"]:
            t = entrada["team"]
            datos[t["name"]] = {
                "puntos": entrada["points"],
                "pj":     entrada["playedGames"],
                "escudo": t["crest"],
            }
        print(f"[API] {codigo}: {len(datos)} equipos cargados")
        return datos
    except Exception as e:
        print(f"[ERROR] obtener_datos_liga({codigo}): {type(e).__name__}: {e}")
        return None


def scrape_bbc_tabla(codigo, url):
    """BBC Sport scraping → {nombre_equipo: {puntos, pj, escudo}} | None si falla.

    BBC muestra nombres sin sufijo FC/AFC (ej. 'Plymouth Argyle', 'Barrow').
    El lookup usa matching por substring (ver _buscar_en_tabla).
    """
    try:
        r = requests.get(url, headers=SCRAPE_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            raise ValueError("Tabla no encontrada en la página")

        datos = {}
        for row in table.find_all("tr")[1:]:   # skip header row
            cells = row.find_all("td")
            if len(cells) < 9:
                continue
            # Col 0: "1Plymouth Argyle" — strip leading position number
            nombre = re.sub(r"^\d+", "", cells[0].get_text(strip=True)).strip()
            pj     = int(cells[1].get_text(strip=True))
            puntos = int(cells[8].get_text(strip=True))
            datos[nombre] = {"puntos": puntos, "pj": pj, "escudo": ""}

        print(f"[BBC] {codigo}: {len(datos)} equipos scrapeados: {sorted(datos.keys())}")
        return datos
    except Exception as e:
        print(f"[ERROR] scrape_bbc_tabla({codigo}): {type(e).__name__}: {e}")
        return None


def _buscar_en_tabla(tabla, nombre_jugador):
    """Lookup con fallback substring: maneja 'Plymouth Argyle' ↔ 'Plymouth Argyle FC'.

    Primero busca coincidencia exacta; si no, busca si el nombre BBC es
    substring del nombre del jugador (o viceversa).
    """
    # Exact match
    if nombre_jugador in tabla:
        return tabla[nombre_jugador]
    # Substring match (case-insensitive)
    nombre_lower = nombre_jugador.lower()
    for bbc_nombre, data in tabla.items():
        bbc_lower = bbc_nombre.lower()
        if bbc_lower in nombre_lower or nombre_lower in bbc_lower:
            return data
    return None


def enriquecer_equipos(equipos_def, datos_por_liga):
    """Combina definición de equipos con datos de API/scraping.

    datos_por_liga[codigo]:
      dict  → datos disponibles (API o scraping exitoso)
      None  → fallo de API o scraping
      ausente → liga manual sin fuente
    """
    resultado = []
    for eq in equipos_def:
        codigo    = eq.get("codigo")
        tabla     = datos_por_liga.get(codigo)   # None si no está o falló

        if tabla is not None:
            d = _buscar_en_tabla(tabla, eq["nombre"])
            if d:
                puntos, pj, escudo = d["puntos"], d["pj"], d.get("escudo", "")
                pendiente = False
                print(f"[OK]   {eq['nombre']} ({codigo}): {puntos} pts, {pj} PJ")
            else:
                puntos, pj, escudo = 0, 0, ""
                pendiente = True
                print(f"[WARN] {eq['nombre']} ({codigo}): nombre no encontrado en la tabla")
        else:
            puntos, pj, escudo = 0, 0, ""
            pendiente = True

        resultado.append({
            "liga":      eq["liga"],
            "nombre":    eq["nombre"],
            "escudo":    escudo,
            "puntos":    puntos,
            "pj":        pj,
            "pendiente": pendiente,
            "id":        eq.get("id"),
            "codigo":    codigo,
        })
    return resultado


def cargar_todos_los_datos():
    """Carga standings de todas las fuentes. Se llama en cada page load."""
    datos = {}
    for codigo in API_LIGAS:
        datos[codigo] = obtener_datos_liga(codigo)
    for codigo, url in BBC_LIGAS.items():
        datos[codigo] = scrape_bbc_tabla(codigo, url)
    return datos


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    datos_por_liga = cargar_todos_los_datos()

    lista = []
    for j in jugadores:
        equipos = enriquecer_equipos(j["equipos"], datos_por_liga)
        lista.append({
            "nombre":  j["nombre"],
            "puntos":  sum(e["puntos"] for e in equipos),
            "pj":      sum(e["pj"] for e in equipos),
            "equipos": equipos,
        })

    lista.sort(key=lambda j: j["puntos"], reverse=True)
    return render_template("index.html", jugadores=lista)



if __name__ == "__main__":
    app.run(debug=True)

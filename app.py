import datetime
import json
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template
from functools import lru_cache
from pathlib import Path

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

# ── Puntos bonus desde bonus.json ────────────────────────────────────────────
# Clave: nombre del equipo exacto. Valor: puntos bonus (entero).
# Las claves que empiezan con "_" se ignoran (son comentarios/notas).
def _cargar_bonus():
    path = Path(__file__).parent / "bonus.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}

BONUS = _cargar_bonus()

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


# Términos de búsqueda para TheSportsDB por nombre de equipo.
# Hampton & Richmond Borough FC no existe en TheSportsDB → queda sin escudo (placeholder).
SPORTSDB_TERMINOS = {
    "Plymouth Argyle FC":         "Plymouth Argyle",
    "Wigan Athletic FC":          "Wigan Athletic",
    "AFC Wimbledon":              "AFC Wimbledon",
    "Notts County FC":            "Notts County",
    "Barrow AFC":                 "Barrow",
    "Oldham Athletic AFC":        "Oldham Athletic",
    "York City FC":               "York City",
    "Boston United FC":           "Boston United",
    "Carlisle United FC":         "Carlisle United",
    "Kidderminster Harriers FC":  "Kidderminster Harriers",
    "Hereford FC":                "Hereford",
    "Chester FC":                 "Chester",
    "Torquay United FC":          "Torquay United",
    "Maidstone United FC":        "Maidstone United",
}

# Escudos hardcodeados para equipos no encontrados en TheSportsDB
ESCUDOS_HARDCODEADOS = {
    "Hampton & Richmond Borough FC": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Hampton_and_Richmond_Badge.png/250px-Hampton_and_Richmond_Badge.png",
}


@lru_cache(maxsize=None)
def obtener_escudo_sportsdb(termino):
    """Consulta TheSportsDB y devuelve la URL del escudo (strBadge).

    Cachea el resultado en memoria para no repetir el request entre page loads.
    Devuelve '' si no encuentra el equipo o si la llamada falla.
    """
    try:
        r = requests.get(
            "https://www.thesportsdb.com/api/v1/json/3/searchteams.php",
            params={"t": termino},
            timeout=5,
        )
        teams = r.json().get("teams") or []
        if teams:
            badge = teams[0].get("strBadge", "")
            print(f"[SPORTSDB] {termino}: {badge[:60] if badge else 'sin escudo'}")
            return badge
    except Exception as e:
        print(f"[ERROR] obtener_escudo_sportsdb({termino}): {e}")
    return ""


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


def enriquecer_equipos(equipos_def, datos_por_liga, equipos_en_vivo=None, pts_prov_dict=None, h2h_equipos=None):
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

        # Si no hay escudo: buscar en TheSportsDB o usar hardcodeado
        if not escudo:
            if eq["nombre"] in ESCUDOS_HARDCODEADOS:
                escudo = ESCUDOS_HARDCODEADOS[eq["nombre"]]
            elif eq["nombre"] in SPORTSDB_TERMINOS:
                escudo = obtener_escudo_sportsdb(SPORTSDB_TERMINOS[eq["nombre"]])

        en_vivo   = _equipo_en_vivo(eq["nombre"], equipos_en_vivo or set())
        h2h_vivo  = eq["nombre"] in (h2h_equipos or set())
        prov_data = _puntos_prov_equipo(eq["nombre"], pts_prov_dict) if (pts_prov_dict is not None and en_vivo) else None
        if prov_data:
            pts_base = prov_data["pts"]
            # H2H ganando: 3 normales + 3 bonus = 6. Empate/derrota: sin bonus.
            pts_prov = 6 if (h2h_vivo and pts_base == 3) else pts_base
            goles = prov_data["marcador"].split("-")
            marcador_vivo = prov_data["marcador"] if prov_data.get("es_local", True) else f"{goles[1]}-{goles[0]}"
        else:
            pts_prov      = None
            marcador_vivo = None

        resultado.append({
            "liga":              eq["liga"],
            "nombre":            eq["nombre"],
            "escudo":            escudo,
            "puntos":            puntos,
            "pj":                pj,
            "pendiente":         pendiente,
            "bonus":             BONUS.get(eq["nombre"], 0),
            "en_vivo":           en_vivo,
            "pts_provisionales": pts_prov,
            "marcador_vivo":     marcador_vivo,
            "h2h_en_vivo":       h2h_vivo,
            "id":                eq.get("id"),
            "codigo":            codigo,
        })
    return resultado


# Mapeo de nombres abreviados/alternativos de BBC → nombre exacto en jugadores.
# BBC usa nombres completos en visually-hidden, pero por si acaso aparecen abreviaciones.
BBC_NOMBRES = {
    # Premier League
    "Man Utd":            "Manchester United FC",
    "Manchester Utd":     "Manchester United FC",
    "Man City":           "Manchester City FC",
    "Wolves":             "Wolverhampton Wanderers FC",
    "Spurs":              "Tottenham Hotspur FC",
    "Newcastle":          "Newcastle United FC",
    "Leeds":              "Leeds United FC",
    "Leicester":          "Leicester City FC",
    # Championship
    "Sheff Utd":          "Sheffield United FC",
    "Sheff Wed":          "Sheffield Wednesday FC",
    "West Brom":          "West Bromwich Albion FC",
    "QPR":                "Queens Park Rangers FC",
    "Stoke":              "Stoke City FC",
    "Swansea":            "Swansea City AFC",
    "Middlesbrough":      "Middlesbrough FC",
    "Coventry":           "Coventry City FC",
    "Blackburn":          "Blackburn Rovers FC",
    "Preston":            "Preston North End FC",
    "Norwich":            "Norwich City FC",
    "Watford":            "Watford FC",
    # League One
    "Wigan":              "Wigan Athletic FC",
    "Plymouth":           "Plymouth Argyle FC",
    "Wimbledon":          "AFC Wimbledon",
    # League Two
    "Notts Co":           "Notts County FC",
    "Oldham":             "Oldham Athletic AFC",
    # National League
    "York":               "York City FC",
    "Carlisle":           "Carlisle United FC",
    "Boston":             "Boston United FC",
    # National League North
    "Kidderminster":      "Kidderminster Harriers FC",
    "Chester":            "Chester FC",
    "Hereford":           "Hereford FC",
    # National League South
    "Torquay":            "Torquay United FC",
    "Maidstone":          "Maidstone United FC",
    "Hampton":            "Hampton & Richmond Borough FC",
}


# Competiciones permitidas para puntos en vivo (lowercase, coincidencia exacta).
LIGAS_EN_VIVO = {
    "premier league",
    "championship",
    "league one",
    "league two",
    "national league",
    "national league north",
    "national league south",
}

# BBC Sport usa nombres alternativos para algunas ligas; los normalizamos al nombre canónico.
def _normalizar_competicion(headings):
    """Dado un contenedor DOM, combina los headings h2+h3 para National League N/S.

    BBC Sport usa dos estructuras:
      - North: <h2>National League N / S</h2> + <h3>North</h3> en el mismo contenedor
      - South: solo <h3>South</h3> en su propio contenedor (el h2 queda en el bloque North)
    En ambos casos devolvemos "national league north" / "national league south".
    Para cualquier otra liga devuelve el texto del primer heading en minúsculas.
    """
    texts = [h.get_text(strip=True).lower() for h in headings]
    if not texts:
        return ""
    h2 = texts[0]
    # Caso: "national league n / s" + sub-heading "north"/"south"
    if h2 == "national league n / s" and len(texts) >= 2:
        sub = texts[1]
        if sub in ("north", "south"):
            return f"national league {sub}"
    # Caso: heading solitario "north" o "south" (bloque South de BBC)
    if h2 in ("north", "south"):
        return f"national league {h2}"
    return h2


def _competicion_del_partido(li):
    """Sube por el DOM desde un <li> de partido buscando el encabezado de competición más cercano.

    BBC Sport agrupa los partidos bajo headings (h2–h5) o elementos con aria-label.
    Estrategia: subir de <li> → <ul>/<ol> → contenedor → buscar hermano previo con heading.
    Devuelve el texto normalizado del heading, o '' si no se encuentra.
    """
    node = li.parent  # normalmente <ul> u <ol>
    while node and node.name not in ("body", "html", "[document]"):
        # Buscar hermanos anteriores que sean o contengan headings
        for sib in node.previous_siblings:
            if not hasattr(sib, "name"):
                continue
            if sib.name in ("h2", "h3", "h4", "h5"):
                return _normalizar_competicion([sib])
            headings = sib.find_all(["h2", "h3", "h4", "h5"])
            if headings:
                return _normalizar_competicion(headings)
        # También revisar headings dentro del propio padre antes de subir más
        parent = node.parent
        if parent:
            headings = parent.find_all(["h2", "h3", "h4", "h5"])
            if headings:
                return _normalizar_competicion(headings)
        node = parent
    return ""


def scrape_equipos_en_vivo():
    """Scrape BBC Sport scores-fixtures para detectar equipos con partido en curso.

    URL: https://www.bbc.com/sport/football/scores-fixtures
    Solo considera partidos de las ligas inglesas definidas en LIGAS_EN_VIVO.
    Ignora Champions League, FA Cup, amistosos y cualquier otra competición.

    Retorna (en_vivo_set, pts_prov_dict):
      - en_vivo_set: set de nombres BBC de equipos en partido en curso
      - pts_prov_dict: {bbc_nombre: {"pts": 3|1|0, "marcador": "X-Y"}}
    Retorna None si el scraping falla → en_vivo queda False para todos.
    """
    try:
        r = requests.get(
            "https://www.bbc.com/sport/football/scores-fixtures",
            headers=SCRAPE_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        en_vivo = set()
        pts_prov = {}  # bbc_nombre → {"pts": 3|1|0, "marcador": "X-Y"}

        for li in soup.find_all("li"):
            # Verificar que este partido específico está en curso
            if not any(
                "in progress" in span.get_text(strip=True).lower()
                for span in li.find_all("span", class_="visually-hidden")
            ):
                continue

            # Verificar que el partido pertenece a una liga permitida
            competicion = _competicion_del_partido(li)
            if competicion not in LIGAS_EN_VIVO:
                print(f"[LIVE-SKIP] partido ignorado (competición: '{competicion}')")
                continue

            hidden = li.find_all("span", class_="visually-hidden")
            # Estructura: hidden[0]="Home score, Away score"  hidden[1]=home  hidden[2]=away
            if len(hidden) >= 3:
                home_name = hidden[1].get_text(strip=True)
                away_name = hidden[2].get_text(strip=True)
                en_vivo.add(home_name)
                en_vivo.add(away_name)

                score_text = hidden[0].get_text(strip=True)
                nums = re.findall(r'\d+', score_text)
                if len(nums) >= 2:
                    home_score, away_score = int(nums[0]), int(nums[1])
                    marcador = f"{home_score}-{away_score}"
                    if home_score > away_score:
                        pts_prov[home_name] = {"pts": 3, "marcador": marcador, "rival": away_name,  "es_local": True}
                        pts_prov[away_name] = {"pts": 0, "marcador": marcador, "rival": home_name, "es_local": False}
                    elif home_score < away_score:
                        pts_prov[home_name] = {"pts": 0, "marcador": marcador, "rival": away_name,  "es_local": True}
                        pts_prov[away_name] = {"pts": 3, "marcador": marcador, "rival": home_name, "es_local": False}
                    else:
                        pts_prov[home_name] = {"pts": 1, "marcador": marcador, "rival": away_name,  "es_local": True}
                        pts_prov[away_name] = {"pts": 1, "marcador": marcador, "rival": home_name, "es_local": False}
                    print(f"[LIVE-OK] {home_name} {marcador} {away_name} ({competicion})")

        print(f"[LIVE] {len(en_vivo)} equipos en vivo: {en_vivo if en_vivo else 'ninguno'}")
        return en_vivo, pts_prov
    except Exception as e:
        print(f"[ERROR] scrape_equipos_en_vivo: {e}")
        return None


def _normalizar_nombre_club(name):
    """Quita sufijos/prefijos FC/AFC para comparación segura entre nombres BBC y canónicos.

    Ejemplos:
      "Chester FC"      → "chester"
      "Wrexham AFC"     → "wrexham"
      "AFC Wimbledon"   → "wimbledon"
      "Manchester United FC" → "manchester united"
    Evita que "Chester" haga substring match contra "Manchester United FC".
    """
    n = name.lower().strip()
    for sufijo in (" fc", " afc"):
        if n.endswith(sufijo):
            return n[: -len(sufijo)].strip()
    for prefijo in ("afc ", "fc "):
        if n.startswith(prefijo):
            return n[len(prefijo) :].strip()
    return n


def _nombre_coincide(bbc_name, canonical_name):
    """True si el nombre BBC corresponde al equipo canónico.

    Orden:
    1. Mapeo explícito en BBC_NOMBRES.
    2. Igualdad exacta de nombres normalizados (sin FC/AFC).
    3. Substring con word-boundary (regex \b) sobre nombres normalizados.
       Evita que 'chester' matchee 'man*chester* united' al nivel de caracteres.
    """
    if BBC_NOMBRES.get(bbc_name) == canonical_name:
        return True
    bbc_norm = _normalizar_nombre_club(bbc_name)
    can_norm = _normalizar_nombre_club(canonical_name)
    if bbc_norm == can_norm:
        return True
    pattern_bbc = r"\b" + re.escape(bbc_norm) + r"\b"
    pattern_can = r"\b" + re.escape(can_norm) + r"\b"
    return bool(re.search(pattern_bbc, can_norm) or re.search(pattern_can, bbc_norm))


def _puntos_prov_equipo(nombre_jugador, pts_prov_dict):
    """Devuelve {"pts": 3|1|0, "marcador": "X-Y"} para un equipo en vivo, o None si no está en partido."""
    for bbc, data in pts_prov_dict.items():
        if _nombre_coincide(bbc, nombre_jugador):
            return data
    return None


def _canonical_team(bbc_name, all_canonical):
    """Resuelve un nombre BBC al nombre canónico del equipo en The Season, o None."""
    for nombre in all_canonical:
        if _nombre_coincide(bbc_name, nombre):
            return nombre
    return None


def _detectar_h2h(pts_prov_dict, jugadores):
    """Detecta partidos en vivo donde ambos equipos pertenecen a distintos jugadores.

    Retorna un set de nombres canónicos de equipos involucrados en un H2H en vivo.
    """
    if not pts_prov_dict:
        return set()

    equipo_a_jugador = {
        eq["nombre"]: j["nombre"]
        for j in jugadores
        for eq in j["equipos"]
    }
    all_canonical = set(equipo_a_jugador.keys())

    h2h = set()
    for bbc_name, data in pts_prov_dict.items():
        rival_bbc = data.get("rival")
        if not rival_bbc:
            continue
        can_home = _canonical_team(bbc_name, all_canonical)
        can_away = _canonical_team(rival_bbc, all_canonical)
        if can_home and can_away:
            jug_home = equipo_a_jugador[can_home]
            jug_away = equipo_a_jugador[can_away]
            if jug_home != jug_away:
                h2h.add(can_home)
                h2h.add(can_away)
                print(f"[H2H] {can_home} ({jug_home}) vs {can_away} ({jug_away})")
    return h2h


def _equipo_en_vivo(nombre_jugador, equipos_en_vivo):
    """Comprueba si un equipo está en vivo usando _nombre_coincide."""
    return any(_nombre_coincide(bbc, nombre_jugador) for bbc in equipos_en_vivo)


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
    live_result    = scrape_equipos_en_vivo()

    if live_result is not None:
        equipos_en_vivo, pts_prov_dict = live_result
    else:
        equipos_en_vivo, pts_prov_dict = set(), None  # None indica fallo de scraping

    h2h_equipos = _detectar_h2h(pts_prov_dict, jugadores)

    lista = []
    for j in jugadores:
        equipos = enriquecer_equipos(j["equipos"], datos_por_liga, equipos_en_vivo, pts_prov_dict, h2h_equipos)
        tiene_en_vivo = any(e["en_vivo"] for e in equipos)
        # Puntos provisionales: solo se muestran si hay al menos un equipo en vivo
        # y el scraping fue exitoso. None → no mostrar.
        if pts_prov_dict is not None and tiene_en_vivo:
            puntos_prov = sum(
                e["pts_provisionales"] for e in equipos if e["pts_provisionales"] is not None
            )
        else:
            puntos_prov = None

        lista.append({
            "nombre":               j["nombre"],
            "puntos":               sum(e["puntos"] + e["bonus"] for e in equipos),
            "pj":                   sum(e["pj"] for e in equipos),
            "equipos":              equipos,
            "puntos_provisionales": puntos_prov,
        })

    lista.sort(key=lambda j: j["puntos"], reverse=True)
    return render_template("index.html", jugadores=lista)



if __name__ == "__main__":
    app.run(debug=True)

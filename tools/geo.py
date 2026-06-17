import requests
import time

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DETAILS_URL = "https://nominatim.openstreetmap.org/details"

HEADERS = {"User-Agent": "ecosystem-mapper/1.0"}

IDIOMAS_POR_PAIS = {
    "es": "es", "mx": "es", "ar": "es", "co": "es", "cl": "es", "pe": "es",
    "ve": "es", "ec": "es", "bo": "es", "py": "es", "uy": "es", "cr": "es",
    "br": "pt", "pt": "pt",
    "fr": "fr", "be": "fr",
    "de": "de", "at": "de", "ch": "de",
    "it": "it",
    "nl": "nl",
    "pl": "pl",
    "ro": "ro",
    "gb": "en", "us": "en", "au": "en", "ca": "en", "nz": "en", "ie": "en",
    "cn": "zh", "tw": "zh",
    "jp": "ja",
    "kr": "ko",
    "ru": "ru",
    "ar_sa": "ar",
}

QUERIES_POR_IDIOMA = {
    "es": {
        "empresas_general": ["empresas destacadas {zona}", "principales empresas {zona}", "parque empresarial {zona}"],
        "empresas_sector": "empresas {sector} {zona}",
        "academia": ["universidades {zona}", "centros investigación I+D {zona}", "formación profesional FP {zona}", "institutos colegios {zona}", "centros tecnológicos {zona}"],
        "administracion": ["ayuntamiento {zona}", "entidades públicas {zona}", "empresa pública {zona}", "servicios sociales {zona}", "agencia desarrollo {zona}"],
        "sociedad": ["ONGs {zona}", "asociaciones vecinales {zona}", "fundaciones sociales {zona}", "asociaciones culturales {zona}", "cooperativas {zona}"],
    },
    "pt": {
        "empresas_general": ["empresas destaque {zona}", "principais empresas {zona}", "polo empresarial {zona}"],
        "empresas_sector": "empresas {sector} {zona}",
        "academia": ["universidades {zona}", "centros pesquisa {zona}", "escolas técnicas {zona}", "institutos {zona}"],
        "administracion": ["prefeitura {zona}", "entidades públicas {zona}", "empresa pública {zona}", "serviços sociais {zona}"],
        "sociedad": ["ONGs {zona}", "associações {zona}", "fundações {zona}", "organizações comunitárias {zona}"],
    },
    "fr": {
        "empresas_general": ["entreprises {zona}", "principales entreprises {zona}", "zone industrielle {zona}"],
        "empresas_sector": "entreprises {sector} {zona}",
        "academia": ["universités {zona}", "centres recherche {zona}", "lycées {zona}", "écoles {zona}"],
        "administracion": ["mairie {zona}", "collectivités {zona}", "services publics {zona}"],
        "sociedad": ["associations {zona}", "ONG {zona}", "fondations {zona}"],
    },
    "de": {
        "empresas_general": ["Unternehmen {zona}", "Firmen {zona}", "Gewerbegebiet {zona}"],
        "empresas_sector": "Unternehmen {sector} {zona}",
        "academia": ["Universitäten {zona}", "Forschungszentren {zona}", "Schulen {zona}"],
        "administracion": ["Gemeinde {zona}", "öffentliche Einrichtungen {zona}", "Stadtverwaltung {zona}"],
        "sociedad": ["Vereine {zona}", "NGOs {zona}", "Stiftungen {zona}"],
    },
    "en": {
        "empresas_general": ["top companies {zona}", "main businesses {zona}", "business park {zona}"],
        "empresas_sector": "{sector} companies {zona}",
        "academia": ["universities {zona}", "research centers {zona}", "schools {zona}", "colleges {zona}"],
        "administracion": ["city council {zona}", "public entities {zona}", "government agencies {zona}"],
        "sociedad": ["NGOs {zona}", "nonprofits {zona}", "community organizations {zona}", "foundations {zona}"],
    },
}


def buscar_zonas(texto: str) -> list[dict]:
    if len(texto) < 3:
        return []
    try:
        params = {
            "q": texto,
            "format": "json",
            "addressdetails": 1,
            "limit": 8,
            "featuretype": "settlement",
        }
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        time.sleep(0.3)
        data = r.json()
        resultados = []
        for item in data:
            addr = item.get("address", {})
            pais_code = addr.get("country_code", "").lower()
            tipo_osm = item.get("type", "")
            clase_osm = item.get("class", "")

            nivel = _inferir_nivel(tipo_osm, clase_osm, addr)
            nombre_display = _construir_nombre(item, addr)

            resultados.append({
                "display": nombre_display,
                "nombre": item.get("name", texto),
                "pais": addr.get("country", ""),
                "pais_code": pais_code,
                "nivel": nivel,
                "lat": float(item.get("lat", 0)),
                "lon": float(item.get("lon", 0)),
                "idioma": IDIOMAS_POR_PAIS.get(pais_code, "en"),
                "contexto": _construir_contexto(addr),
            })
        return resultados
    except Exception:
        return []


def _inferir_nivel(tipo_osm: str, clase_osm: str, addr: dict) -> str:
    if tipo_osm in ["country"]:
        return "País"
    if tipo_osm in ["state", "region", "province"]:
        return "Región"
    if tipo_osm in ["county", "municipality"] or clase_osm == "boundary":
        return "Comarca"
    if tipo_osm in ["city", "town"]:
        return "Ciudad"
    if tipo_osm in ["suburb", "quarter", "neighbourhood", "borough", "district"]:
        return "Distrito"
    if tipo_osm in ["village", "hamlet"]:
        return "Ciudad"
    if addr.get("suburb") or addr.get("neighbourhood"):
        return "Barrio"
    return "Ciudad"


def _construir_nombre(item: dict, addr: dict) -> str:
    partes = []
    nombre = item.get("name") or item.get("display_name", "").split(",")[0]
    partes.append(nombre)
    if addr.get("city") and addr["city"] != nombre:
        partes.append(addr["city"])
    elif addr.get("town") and addr["town"] != nombre:
        partes.append(addr["town"])
    if addr.get("state") and addr.get("state") != nombre:
        partes.append(addr["state"])
    if addr.get("country"):
        partes.append(addr["country"])
    return ", ".join(dict.fromkeys(partes))


def _construir_contexto(addr: dict) -> str:
    partes = []
    for key in ["city", "town", "state", "country"]:
        val = addr.get(key)
        if val:
            partes.append(val)
    return ", ".join(dict.fromkeys(partes))


def get_queries(categoria: str, zona_info: dict, sectores: list[str] = None) -> list[str]:
    idioma = zona_info.get("idioma", "en")
    if idioma not in QUERIES_POR_IDIOMA:
        idioma = "en"

    plantillas = QUERIES_POR_IDIOMA[idioma]
    nombre = zona_info.get("nombre", "")
    contexto = zona_info.get("contexto", "")
    zona_busqueda = f"{nombre} {contexto}".strip() if contexto else nombre

    queries = []

    if categoria == "empresas":
        for t in plantillas["empresas_general"]:
            queries.append(t.format(zona=zona_busqueda))
        sects = sectores if sectores else []
        for s in sects[:5]:
            queries.append(plantillas["empresas_sector"].format(sector=s.lower(), zona=zona_busqueda))

    elif categoria == "academia":
        for t in plantillas["academia"]:
            queries.append(t.format(zona=zona_busqueda))

    elif categoria == "administracion":
        for t in plantillas["administracion"]:
            queries.append(t.format(zona=zona_busqueda))

    elif categoria == "sociedad":
        for t in plantillas["sociedad"]:
            queries.append(t.format(zona=zona_busqueda))

    return queries

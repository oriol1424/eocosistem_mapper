import requests
import time

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
    "gb": "en", "us": "en", "au": "en", "ca": "en", "nz": "en", "ie": "en",
    "cn": "zh", "jp": "ja", "kr": "ko", "ru": "ru",
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


def buscar_zonas(texto: str, geoapify_key: str) -> list[dict]:
    if len(texto) < 3 or not geoapify_key:
        return []
    try:
        url = "https://api.geoapify.com/v1/geocode/autocomplete"
        params = {
            "text": texto,
            "limit": 8,
            "format": "json",
            "apiKey": geoapify_key,
        }
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        resultados = []
        for item in data.get("results", []):
            props = item
            pais_code = props.get("country_code", "").lower()
            nivel = _inferir_nivel(props)
            nombre_display = _construir_nombre(props)
            contexto = _construir_contexto(props)

            resultados.append({
                "display": nombre_display,
                "nombre": props.get("name") or props.get("city") or props.get("county") or texto,
                "pais": props.get("country", ""),
                "pais_code": pais_code,
                "nivel": nivel,
                "lat": props.get("lat", 0),
                "lon": props.get("lon", 0),
                "idioma": IDIOMAS_POR_PAIS.get(pais_code, "en"),
                "contexto": contexto,
            })
        return resultados
    except Exception:
        return []


def _inferir_nivel(props: dict) -> str:
    result_type = props.get("result_type", "")
    if result_type == "country":
        return "País"
    if result_type in ["state", "region", "province"]:
        return "Región"
    if result_type == "county":
        return "Comarca"
    if result_type == "city":
        return "Ciudad"
    if result_type in ["suburb", "district", "borough"]:
        return "Distrito"
    if result_type == "neighbourhood":
        return "Barrio"
    if props.get("suburb"):
        return "Barrio"
    if props.get("district"):
        return "Distrito"
    if props.get("city"):
        return "Ciudad"
    return "Ciudad"


def _construir_nombre(props: dict) -> str:
    partes = []
    for key in ["name", "suburb", "district", "city", "county", "state", "country"]:
        val = props.get(key)
        if val and val not in partes:
            partes.append(val)
        if len(partes) >= 4:
            break
    return ", ".join(partes) if partes else props.get("formatted", "")


def _construir_contexto(props: dict) -> str:
    partes = []
    for key in ["city", "county", "state", "country"]:
        val = props.get(key)
        if val and val not in partes:
            partes.append(val)
    return ", ".join(partes)


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
        for s in (sectores or [])[:5]:
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

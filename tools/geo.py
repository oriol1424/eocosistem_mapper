import requests
import time

HEADERS = {"User-Agent": "ecosystem-mapper/1.0"}

IDIOMAS_POR_PAIS = {
    "es": "es", "mx": "es", "ar": "es", "co": "es", "cl": "es", "pe": "es",
    "ve": "es", "ec": "es", "bo": "es", "py": "es", "uy": "es", "cr": "es",
    "br": "pt", "pt": "pt",
    "fr": "fr", "be": "fr",
    "de": "de", "at": "de", "ch": "de",
    "it": "it", "nl": "nl", "pl": "pl",
    "gb": "en", "us": "en", "au": "en", "ca": "en", "nz": "en", "ie": "en",
    "cn": "zh", "jp": "ja", "kr": "ko", "ru": "ru",
}

QUERIES_POR_IDIOMA = {
    "es": {
        "empresas_general": [
            "startups {zona}", "pymes destacadas {zona}",
            "empresas multinacionales {zona}", "cooperativas empresas {zona}",
            "principales empresas {zona}", "parque empresarial polígono {zona}",
            "cámara de comercio empresas {zona}",
        ],
        "empresas_sector": "empresas {sector} {zona}",
        "academia_general": [
            "universidades públicas privadas {zona}",
            "escuelas universitarias {zona}",
            "másteres posgrados {zona}",
            "doctorado programas PhD {zona}",
            "formación profesional FP grado medio superior {zona}",
            "institutos colegios públicos {zona}",
            "centros investigación I+D {zona}",
            "centros tecnológicos innovación {zona}",
        ],
        "administracion": [
            "ayuntamiento {zona}", "diputación consell {zona}",
            "entidades públicas {zona}", "empresa pública {zona}",
            "servicios sociales públicos {zona}", "agencia desarrollo {zona}",
            "biblioteca pública {zona}", "centro cívico {zona}",
        ],
        "sociedad": [
            "ONGs {zona}", "asociaciones vecinales {zona}",
            "fundaciones sociales {zona}", "asociaciones culturales {zona}",
            "cooperativas sociales {zona}", "colectivos ciudadanos {zona}",
            "organizaciones voluntariado {zona}",
        ],
    },
    "pt": {
        "empresas_general": [
            "startups {zona}", "pequenas médias empresas {zona}",
            "multinacionais {zona}", "cooperativas {zona}",
            "principais empresas {zona}", "polo empresarial {zona}",
        ],
        "empresas_sector": "empresas {sector} {zona}",
        "academia_general": [
            "universidades {zona}", "mestrado doutorado {zona}",
            "escolas técnicas profissionais {zona}",
            "centros pesquisa {zona}", "institutos tecnológicos {zona}",
        ],
        "administracion": [
            "prefeitura {zona}", "entidades públicas {zona}",
            "empresa pública {zona}", "serviços sociais {zona}",
            "biblioteca pública {zona}",
        ],
        "sociedad": [
            "ONGs {zona}", "associações {zona}", "fundações {zona}",
            "organizações comunitárias {zona}", "cooperativas sociais {zona}",
        ],
    },
    "fr": {
        "empresas_general": [
            "startups {zona}", "PME {zona}", "grandes entreprises {zona}",
            "coopératives {zona}", "entreprises {zona}", "zone industrielle {zona}",
        ],
        "empresas_sector": "entreprises {sector} {zona}",
        "academia_general": [
            "universités {zona}", "grandes écoles {zona}",
            "masters doctorats {zona}", "lycées professionnels {zona}",
            "centres recherche {zona}",
        ],
        "administracion": [
            "mairie {zona}", "collectivités {zona}",
            "services publics {zona}", "bibliothèque {zona}",
        ],
        "sociedad": [
            "associations {zona}", "ONG {zona}",
            "fondations {zona}", "coopératives sociales {zona}",
        ],
    },
    "de": {
        "empresas_general": [
            "Startups {zona}", "KMU Unternehmen {zona}",
            "Konzerne {zona}", "Genossenschaften {zona}",
            "Firmen {zona}", "Gewerbegebiet {zona}",
        ],
        "empresas_sector": "Unternehmen {sector} {zona}",
        "academia_general": [
            "Universitäten {zona}", "Master Doktorat {zona}",
            "Berufsschulen {zona}", "Forschungszentren {zona}",
        ],
        "administracion": [
            "Gemeindeverwaltung {zona}", "öffentliche Einrichtungen {zona}",
            "Stadtbibliothek {zona}",
        ],
        "sociedad": [
            "Vereine {zona}", "NGOs {zona}",
            "Stiftungen {zona}", "Genossenschaften {zona}",
        ],
    },
    "en": {
        "empresas_general": [
            "startups {zona}", "SMEs small businesses {zona}",
            "multinational companies {zona}", "cooperatives {zona}",
            "top companies {zona}", "business park {zona}",
            "chamber of commerce {zona}",
        ],
        "empresas_sector": "{sector} companies {zona}",
        "academia_general": [
            "universities {zona}", "master programs {zona}",
            "PhD doctorate programs {zona}", "vocational colleges {zona}",
            "research centers {zona}", "technology institutes {zona}",
        ],
        "administracion": [
            "city council {zona}", "public entities {zona}",
            "government agencies {zona}", "public library {zona}",
            "community center {zona}",
        ],
        "sociedad": [
            "NGOs nonprofits {zona}", "community organizations {zona}",
            "foundations {zona}", "neighborhood associations {zona}",
            "volunteer organizations {zona}",
        ],
    },
}


def buscar_zonas(texto: str, geoapify_key: str) -> list[dict]:
    if len(texto) < 3 or not geoapify_key:
        return []
    try:
        url = "https://api.geoapify.com/v1/geocode/autocomplete"
        params = {"text": texto, "limit": 8, "format": "json", "apiKey": geoapify_key}
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
    if result_type == "country": return "País"
    if result_type in ["state", "region", "province"]: return "Región"
    if result_type == "county": return "Comarca"
    if result_type == "city": return "Ciudad"
    if result_type in ["suburb", "district", "borough"]: return "Distrito"
    if result_type == "neighbourhood": return "Barrio"
    if props.get("suburb"): return "Barrio"
    if props.get("district"): return "Distrito"
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
    queries = []

    if categoria == "empresas":
        for t in plantillas["empresas_general"]:
            queries.append(t.format(zona=nombre))
        for s in (sectores or [])[:6]:
            queries.append(plantillas["empresas_sector"].format(sector=s.lower(), zona=nombre))

    elif categoria == "academia":
        for t in plantillas["academia_general"]:
            queries.append(t.format(zona=nombre))
        if sectores:
            for s in sectores[:3]:
                queries.append(f"{s.lower()} {nombre}")

    elif categoria == "administracion":
        for t in plantillas["administracion"]:
            queries.append(t.format(zona=nombre))

    elif categoria == "sociedad":
        for t in plantillas["sociedad"]:
            queries.append(t.format(zona=nombre))
        if sectores:
            for s in sectores[:3]:
                queries.append(f"asociación {s.lower()} {nombre}")

    return queries

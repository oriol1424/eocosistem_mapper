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
        ],
        "sociedad": [
            "ONGs {zona}", "associações {zona}", "fundações {zona}",
            "organizações comunitárias {zona}",
        ],
    },
    "fr": {
        "empresas_general": [
            "startups {zona}", "PME {zona}", "grandes entreprises {zona}",
            "entreprises {zona}", "zone industrielle {zona}",
        ],
        "empresas_sector": "entreprises {sector} {zona}",
        "academia_general": [
            "universités {zona}", "grandes écoles {zona}",
            "masters doctorats {zona}", "lycées professionnels {zona}",
            "centres recherche {zona}",
        ],
        "administracion": [
            "mairie {zona}", "collectivités {zona}", "services publics {zona}",
        ],
        "sociedad": [
            "associations {zona}", "ONG {zona}", "fondations {zona}",
        ],
    },
    "en": {
        "empresas_general": [
            "startups {zona}", "SMEs small businesses {zona}",
            "multinational companies {zona}", "top companies {zona}",
            "business park {zona}", "chamber of commerce {zona}",
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
        ],
        "sociedad": [
            "NGOs nonprofits {zona}", "community organizations {zona}",
            "foundations {zona}", "neighborhood associations {zona}",
        ],
    },
    "de": {
        "empresas_general": [
            "Startups {zona}", "KMU Unternehmen {zona}",
            "Firmen {zona}", "Gewerbegebiet {zona}",
        ],
        "empresas_sector": "Unternehmen {sector} {zona}",
        "academia_general": [
            "Universitäten {zona}", "Master Doktorat {zona}",
            "Berufsschulen {zona}", "Forschungszentren {zona}",
        ],
        "administracion": [
            "Gemeindeverwaltung {zona}", "öffentliche Einrichtungen {zona}",
        ],
        "sociedad": [
            "Vereine {zona}", "NGOs {zona}", "Stiftungen {zona}",
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
        vistos = set()

        for item in data.get("results", []):
            props = item
            pais_code = props.get("country_code", "").lower()
            nivel = _inferir_nivel(props)
            nombre_zona = _extraer_nombre_zona(props, nivel)
            nombre_display = _construir_display(props, nivel)
            contexto = _construir_contexto(props, nivel)

            # Deduplicar opciones del desplegable
            key_dedup = f"{nombre_zona}|{pais_code}|{nivel}"
            if key_dedup in vistos:
                continue
            vistos.add(key_dedup)

            resultados.append({
                "display": nombre_display,
                "nombre": nombre_zona,
                "pais": props.get("country", ""),
                "pais_code": pais_code,
                "nivel": nivel,
                "lat": props.get("lat", 0),
                "lon": props.get("lon", 0),
                "idioma": IDIOMAS_POR_PAIS.get(pais_code, "en"),
                "contexto": contexto,
                "ciudad": props.get("city") or props.get("town") or "",
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


def _extraer_nombre_zona(props: dict, nivel: str) -> str:
    """
    Extrae el nombre específico de la zona según el nivel.
    Para Barrio/Distrito prioriza suburb/district sobre name/city.
    """
    if nivel in ["Barrio", "Distrito"]:
        # Para distritos: priorizar suburb o district sobre name
        for key in ["suburb", "district", "name"]:
            val = props.get(key)
            if val:
                ciudad = props.get("city") or props.get("town") or ""
                # Evitar devolver el nombre de la ciudad como nombre del distrito
                if val != ciudad:
                    return val
        # Fallback: usar formatted y coger la primera parte
        formatted = props.get("formatted", "")
        if formatted:
            return formatted.split(",")[0].strip()
    elif nivel == "Ciudad":
        return props.get("city") or props.get("town") or props.get("name", "")
    elif nivel in ["Comarca", "Región"]:
        return props.get("county") or props.get("state") or props.get("name", "")
    elif nivel == "País":
        return props.get("country") or props.get("name", "")

    return props.get("name", "") or props.get("formatted", "").split(",")[0].strip()


def _construir_display(props: dict, nivel: str) -> str:
    """Construye el texto que ve el usuario en el desplegable."""
    nombre = _extraer_nombre_zona(props, nivel)
    partes = [nombre]
    ciudad = props.get("city") or props.get("town") or ""
    estado = props.get("state") or props.get("county") or ""
    pais = props.get("country") or ""

    for val in [ciudad, estado, pais]:
        if val and val not in partes:
            partes.append(val)
        if len(partes) >= 4:
            break
    return ", ".join(partes)


def _construir_contexto(props: dict, nivel: str) -> str:
    """Contexto geográfico para afinar búsquedas (ciudad, región)."""
    partes = []
    for key in ["city", "town", "county", "state"]:
        val = props.get(key)
        if val and val not in partes:
            partes.append(val)
        if len(partes) >= 2:
            break
    return ", ".join(partes)


def _zona_busqueda(zona_info: dict) -> tuple:
    """
    Devuelve (zona_especifica, zona_ciudad) según el nivel.
    Para Barrio/Distrito combina nombre del distrito + ciudad.
    """
    nombre = zona_info.get("nombre", "")
    nivel = zona_info.get("nivel", "Ciudad")
    ciudad = zona_info.get("ciudad", "") or zona_info.get("contexto", "").split(",")[0].strip()

    if nivel in ["Barrio", "Distrito"] and ciudad and ciudad.lower() != nombre.lower():
        zona_esp = f"{nombre} {ciudad}"
        zona_ciudad = ciudad
    else:
        zona_esp = nombre
        zona_ciudad = nombre

    return zona_esp, zona_ciudad


def get_queries(categoria: str, zona_info: dict, sectores: list = None) -> list:
    idioma = zona_info.get("idioma", "en")
    if idioma not in QUERIES_POR_IDIOMA:
        idioma = "en"

    plantillas = QUERIES_POR_IDIOMA[idioma]
    zona_esp, zona_ciudad = _zona_busqueda(zona_info)
    nivel = zona_info.get("nivel", "Ciudad")
    queries = []

    if categoria == "empresas":
        for t in plantillas["empresas_general"]:
            queries.append(t.format(zona=zona_esp))
        # Para distritos añadir queries con solo la ciudad para no perder actores
        if nivel in ["Barrio", "Distrito"] and zona_ciudad != zona_esp:
            for t in plantillas["empresas_general"][:3]:
                q = t.format(zona=zona_ciudad)
                if q not in queries:
                    queries.append(q)
        for s in (sectores or [])[:6]:
            queries.append(plantillas["empresas_sector"].format(sector=s.lower(), zona=zona_esp))

    elif categoria == "academia":
        for t in plantillas["academia_general"]:
            queries.append(t.format(zona=zona_esp))
        if nivel in ["Barrio", "Distrito"] and zona_ciudad != zona_esp:
            for t in plantillas["academia_general"][:4]:
                q = t.format(zona=zona_ciudad)
                if q not in queries:
                    queries.append(q)
        for s in (sectores or [])[:3]:
            q = f"{s.lower()} {zona_esp}"
            if q not in queries:
                queries.append(q)

    elif categoria == "administracion":
        for t in plantillas["administracion"]:
            queries.append(t.format(zona=zona_esp))
        if nivel in ["Barrio", "Distrito"] and zona_ciudad != zona_esp:
            for t in plantillas["administracion"][:3]:
                q = t.format(zona=zona_ciudad)
                if q not in queries:
                    queries.append(q)

    elif categoria == "sociedad":
        for t in plantillas["sociedad"]:
            queries.append(t.format(zona=zona_esp))
        if nivel in ["Barrio", "Distrito"] and zona_ciudad != zona_esp:
            for t in plantillas["sociedad"][:3]:
                q = t.format(zona=zona_ciudad)
                if q not in queries:
                    queries.append(q)
        for s in (sectores or [])[:3]:
            q = f"asociación {s.lower()} {zona_esp}"
            if q not in queries:
                queries.append(q)

    return queries

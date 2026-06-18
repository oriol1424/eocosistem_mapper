import requests
import time
import threading

OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS_OSM = {"User-Agent": "ecosystem-mapper/1.0 (educational project)"}

_osm_lock = threading.Lock()
_last_osm_call = [0.0]


def _osm_pause():
    """Garantiza 1.2s entre llamadas a OSM para no ser bloqueado."""
    with _osm_lock:
        elapsed = time.time() - _last_osm_call[0]
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        _last_osm_call[0] = time.time()


def _construir_query_geocode(actor: dict, zona_info: dict) -> str:
    """
    Construye la query de geocodificación priorizando la dirección extraída por el LLM.
    Si hay dirección usa esa — es mucho más precisa que solo el nombre.
    Si no hay dirección usa nombre + contexto geográfico.
    """
    direccion = actor.get("direccion") or actor.get("ubicacion") or ""
    nombre = actor.get("nombre", "")
    pais = zona_info.get("pais", "")
    ciudad = zona_info.get("ciudad", "") or zona_info.get("contexto", "").split(",")[0].strip()

    if direccion and len(direccion) > 5:
        # Tenemos dirección — usarla directamente, añadir ciudad si no está incluida
        if ciudad and ciudad.lower() not in direccion.lower():
            return f"{direccion}, {ciudad}"
        return direccion
    else:
        # Sin dirección — usar nombre + ciudad para dar contexto geográfico
        if ciudad:
            return f"{nombre}, {ciudad}, {pais}".strip(", ")
        return f"{nombre}, {pais}".strip(", ")


def _buscar_osm_nominatim(actor: dict, zona_info: dict) -> dict:
    """Busca coordenadas via OSM Nominatim usando dirección si está disponible."""
    try:
        _osm_pause()
        query = _construir_query_geocode(actor, zona_info)
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
        }
        r = requests.get(OSM_NOMINATIM_URL, params=params, headers=HEADERS_OSM, timeout=5)
        data = r.json()
        if not data:
            return {}
        item = data[0]
        addr = item.get("address", {})
        result = {
            "lat": float(item.get("lat", 0)),
            "lon": float(item.get("lon", 0)),
        }
        # Solo sobreescribir dirección si el actor no tenía una
        if not actor.get("direccion"):
            result["direccion"] = _formatear_direccion_osm(addr)
        return result
    except Exception:
        return {}


def _buscar_opencage(actor: dict, zona_info: dict, api_key: str) -> dict:
    """Busca coordenadas via OpenCage usando dirección si está disponible."""
    if not api_key:
        return {}
    try:
        query = _construir_query_geocode(actor, zona_info)
        params = {
            "q": query,
            "key": api_key,
            "limit": 1,
            "no_annotations": 1,
            "language": zona_info.get("idioma", "es"),
        }
        r = requests.get(OPENCAGE_URL, params=params, timeout=5)
        data = r.json()
        results = data.get("results", [])
        if not results:
            return {}
        item = results[0]
        comp = item.get("components", {})
        geo = item.get("geometry", {})
        result = {
            "lat": geo.get("lat", 0),
            "lon": geo.get("lng", 0),
        }
        if not actor.get("direccion"):
            result["direccion"] = _formatear_direccion_opencage(comp)
        return result
    except Exception:
        return {}


def _buscar_osm_overpass(nombre: str, zona_info: dict) -> dict:
    """Busca datos detallados via OSM Overpass (para administración pública)."""
    try:
        _osm_pause()
        lat = zona_info.get("lat", 0)
        lon = zona_info.get("lon", 0)
        if not lat or not lon:
            return {}
        nombre_safe = nombre.replace('"', "").replace("'", "")[:40]
        query = f"""
[out:json][timeout:8];
(
  node["name"~"{nombre_safe}",i](around:15000,{lat},{lon});
  way["name"~"{nombre_safe}",i](around:15000,{lat},{lon});
);
out body 1;
"""
        r = requests.post(OSM_OVERPASS_URL, data={"data": query}, timeout=10)
        data = r.json()
        elements = data.get("elements", [])
        if not elements:
            return {}
        el = elements[0]
        tags = el.get("tags", {})
        addr_parts = filter(None, [
            tags.get("addr:street", ""),
            tags.get("addr:housenumber", ""),
            tags.get("addr:postcode", ""),
            tags.get("addr:city", ""),
        ])
        direccion = ", ".join(addr_parts)
        result = {}
        if direccion:
            result["direccion"] = direccion
        if tags.get("phone"):
            result["contacto"] = tags["phone"]
        if tags.get("website"):
            result["web"] = tags["website"]
        if tags.get("opening_hours"):
            result["horarios"] = tags["opening_hours"]
        if el.get("lat"):
            result["lat"] = el["lat"]
            result["lon"] = el.get("lon", 0)
        return result
    except Exception:
        return {}


def _formatear_direccion_osm(addr: dict) -> str:
    partes = filter(None, [
        addr.get("road", ""),
        addr.get("house_number", ""),
        addr.get("postcode", ""),
        addr.get("city") or addr.get("town") or addr.get("village", ""),
        addr.get("country", ""),
    ])
    return ", ".join(partes)


def _formatear_direccion_opencage(comp: dict) -> str:
    partes = filter(None, [
        comp.get("road", ""),
        comp.get("house_number", ""),
        comp.get("postcode", ""),
        comp.get("city") or comp.get("town") or comp.get("village", ""),
        comp.get("country", ""),
    ])
    return ", ".join(partes)


def _combinar_resultados(osm: dict, opencage: dict, overpass: dict) -> dict:
    """Combina resultados de las tres fuentes, priorizando el más completo."""
    combined = {}
    for fuente in [overpass, osm, opencage]:
        for key, val in fuente.items():
            if val and not combined.get(key):
                combined[key] = val
    return combined


def enriquecer_actor(actor: dict, categoria: str, zona_info: dict, opencage_key: str = None) -> dict:
    """Enriquece un actor combinando OSM Nominatim + OpenCage + Overpass.
    Prioriza la dirección ya extraída por el LLM para geocodificar con precisión."""
    nombre = actor.get("nombre", "")
    if not nombre:
        return actor

    osm_result = {}
    opencage_result = {}
    overpass_result = {}

    if categoria == "Administración pública":
        overpass_result = _buscar_osm_overpass(nombre, zona_info)
        if not overpass_result.get("lat"):
            osm_result = _buscar_osm_nominatim(actor, zona_info)
            if opencage_key:
                opencage_result = _buscar_opencage(actor, zona_info, opencage_key)
    else:
        osm_result = _buscar_osm_nominatim(actor, zona_info)
        if opencage_key:
            opencage_result = _buscar_opencage(actor, zona_info, opencage_key)

    enriched = _combinar_resultados(osm_result, opencage_result, overpass_result)

    for key, val in enriched.items():
        if val and not actor.get(key):
            actor[key] = val

    return actor


def _verificar_en_zona(actor: dict, zona_info: dict) -> str:
    """
    Verifica si el actor está dentro de la zona usando coordenadas.
    Devuelve: "dentro" / "fuera" / "sin_datos"
    """
    import math

    actor_lat = actor.get("lat", 0)
    actor_lon = actor.get("lon", 0)
    zona_lat = zona_info.get("lat", 0)
    zona_lon = zona_info.get("lon", 0)

    if not actor_lat or not actor_lon or not zona_lat or not zona_lon:
        return "sin_datos"

    # Distancia Haversine en km
    R = 6371
    dlat = math.radians(actor_lat - zona_lat)
    dlon = math.radians(actor_lon - zona_lon)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(zona_lat)) * math.cos(math.radians(actor_lat)) * math.sin(dlon/2)**2
    distancia = R * 2 * math.asin(math.sqrt(a))

    # Radio según nivel geográfico
    radios = {
        "Barrio": 1.5,
        "Distrito": 4.0,
        "Ciudad": 20.0,
        "Comarca": 50.0,
        "Región": 200.0,
        "País": 9999.0,
    }
    radio = radios.get(zona_info.get("nivel", "Ciudad"), 20.0)

    return "dentro" if distancia <= radio else "fuera"


def _construir_verificacion(actor: dict, zona_info: dict) -> str:
    """Construye el texto de verificación combinando coordenadas y presencia."""
    geo = _verificar_en_zona(actor, zona_info)
    presencia = actor.get("presencia", "desconocido")
    nota = actor.get("nota_presencia", "")

    if geo == "dentro":
        if presencia == "sede":
            return f"✅ Sede en zona"
        elif presencia == "campus":
            return f"✅ Campus en zona — {nota}" if nota else "✅ Campus en zona"
        elif presencia == "delegacion":
            return f"✅ Delegación en zona — {nota}" if nota else "✅ Delegación en zona"
        else:
            return "✅ Dentro de zona"
    elif geo == "fuera":
        if presencia in ["campus", "delegacion"]:
            return f"⚠️ {presencia.capitalize()} fuera de zona — revisar"
        return "⚠️ Fuera de zona — revisar"
    else:
        if presencia == "sede":
            return "❓ Sede — dirección no confirmada"
        elif presencia == "campus":
            return f"❓ Campus — {nota}" if nota else "❓ Campus — sin coordenadas"
        elif presencia == "delegacion":
            return f"❓ Delegación — {nota}" if nota else "❓ Delegación — sin coordenadas"
        return "❓ Sin dirección confirmada"


def enriquecer_lista(actores: list, categoria: str, zona_info: dict,
                     opencage_key: str = None, progress_callback=None) -> list:
    """Enriquece una lista de actores con pausas inteligentes y verificación geográfica."""
    enriquecidos = []
    total = len(actores)
    for i, actor in enumerate(actores):
        if progress_callback:
            progress_callback(i, total, actor.get("nombre", "")[:40])
        actor = enriquecer_actor(actor, categoria, zona_info, opencage_key)
        actor["verificacion"] = _construir_verificacion(actor, zona_info)
        enriquecidos.append(actor)
    return enriquecidos

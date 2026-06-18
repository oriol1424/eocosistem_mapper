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


def _buscar_osm_nominatim(nombre: str, zona_info: dict) -> dict:
    """Busca dirección via OSM Nominatim."""
    try:
        _osm_pause()
        pais = zona_info.get("pais", "")
        query = f"{nombre}, {pais}".strip(", ")
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
        return {
            "direccion": _formatear_direccion_osm(addr),
            "lat": float(item.get("lat", 0)),
            "lon": float(item.get("lon", 0)),
        }
    except Exception:
        return {}


def _buscar_opencage(nombre: str, zona_info: dict, api_key: str) -> dict:
    """Busca dirección via OpenCage."""
    if not api_key:
        return {}
    try:
        pais = zona_info.get("pais", "")
        query = f"{nombre}, {pais}".strip(", ")
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
        return {
            "direccion": _formatear_direccion_opencage(comp),
            "lat": geo.get("lat", 0),
            "lon": geo.get("lng", 0),
        }
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
    """Enriquece un actor combinando OSM Nominatim + OpenCage + Overpass."""
    nombre = actor.get("nombre", "")
    if not nombre:
        return actor

    osm_result = {}
    opencage_result = {}
    overpass_result = {}

    if categoria == "Administración pública":
        overpass_result = _buscar_osm_overpass(nombre, zona_info)
        if not overpass_result.get("direccion"):
            osm_result = _buscar_osm_nominatim(nombre, zona_info)
            if opencage_key:
                opencage_result = _buscar_opencage(nombre, zona_info, opencage_key)
    else:
        osm_result = _buscar_osm_nominatim(nombre, zona_info)
        if opencage_key:
            opencage_result = _buscar_opencage(nombre, zona_info, opencage_key)

    enriched = _combinar_resultados(osm_result, opencage_result, overpass_result)

    for key, val in enriched.items():
        if val and not actor.get(key):
            actor[key] = val

    return actor


def enriquecer_lista(actores: list, categoria: str, zona_info: dict,
                     opencage_key: str = None, progress_callback=None) -> list:
    """Enriquece una lista de actores con pausas inteligentes."""
    enriquecidos = []
    total = len(actores)
    for i, actor in enumerate(actores):
        if progress_callback:
            progress_callback(i, total, actor.get("nombre", "")[:40])
        actor = enriquecer_actor(actor, categoria, zona_info, opencage_key)
        enriquecidos.append(actor)
    return enriquecidos

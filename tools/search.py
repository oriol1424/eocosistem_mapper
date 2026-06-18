import time
import requests
from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 5, tavily_key: str = None,
               serper_key: str = None, zona_info: dict = None) -> list[dict]:
    """
    Busca en la web usando cascada de proveedores.
    Con serper_key activa filtro geográfico por coordenadas.
    """
    results = []

    if serper_key:
        results = _search_serper(query, max_results, serper_key, zona_info)

    if not results and tavily_key:
        results = _search_tavily(query, max_results, tavily_key, zona_info)

    if not results:
        results = _search_duckduckgo(query, max_results)

    return results


def _search_serper(query: str, max_results: int, api_key: str, zona_info: dict = None) -> list[dict]:
    try:
        payload = {"q": query, "num": max_results}

        if zona_info:
            pais_code = zona_info.get("pais_code", "")
            if pais_code:
                payload["gl"] = pais_code.lower()
            idioma = zona_info.get("idioma", "es")
            payload["hl"] = idioma

        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        data = response.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", "")
            }
            for r in data.get("organic", [])
        ]
    except Exception:
        return []


def _search_tavily(query: str, max_results: int, api_key: str, zona_info: dict = None) -> list[dict]:
    try:
        payload = {"api_key": api_key, "query": query, "max_results": max_results}
        response = requests.post("https://api.tavily.com/search", json=payload, timeout=10)
        data = response.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")
            }
            for r in data.get("results", [])
        ]
    except Exception:
        return []


def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
            time.sleep(0.5)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                }
                for r in raw
            ]
    except Exception:
        return []


def format_results_for_llm(results: list[dict]) -> str:
    if not results:
        return "No se encontraron resultados."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {r['snippet']}")
    return "\n\n".join(lines)

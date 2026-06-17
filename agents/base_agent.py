import json
import re
from tools.search import search_web, format_results_for_llm
from tools.llm import get_llm_response


SYSTEM_PROMPT = """Eres un experto en análisis de ecosistemas territoriales.
Tu tarea es extraer información estructurada sobre actores de un ecosistema a partir de resultados de búsqueda web.
Siempre responde ÚNICAMENTE con JSON válido, sin texto adicional, sin markdown, sin explicaciones."""

EXTRACTION_PROMPT = """A partir de los siguientes resultados de búsqueda sobre "{query}", extrae todos los actores relevantes.

Resultados:
{results}

Devuelve un JSON con esta estructura exacta:
{{
  "actores": [
    {{
      "nombre": "Nombre oficial de la organización",
      "tipo": "tipo específico (ej: empresa tecnológica, universidad pública, ONG ambiental...)",
      "descripcion": "Descripción breve de 1-2 frases de qué hace",
      "web": "URL si está disponible, sino null",
      "sector": "sector o área de actividad principal",
      "ubicacion": "ciudad o zona específica si se menciona",
      "contacto": "email o teléfono si aparece, sino null"
    }}
  ]
}}

Incluye solo actores claramente identificados. Si no hay actores relevantes, devuelve {{"actores": []}}"""


class BaseAgent:
    def __init__(self, provider: str, api_key: str, tavily_key: str = None, serper_key: str = None):
        self.provider = provider
        self.api_key = api_key
        self.tavily_key = tavily_key
        self.serper_key = serper_key

    def _search_and_extract(self, query: str) -> list[dict]:
        results = search_web(query, max_results=8, tavily_key=self.tavily_key, serper_key=self.serper_key)
        if not results:
            return []

        formatted = format_results_for_llm(results)
        user_prompt = EXTRACTION_PROMPT.format(query=query, results=formatted)

        try:
            raw = get_llm_response(self.provider, self.api_key, SYSTEM_PROMPT, user_prompt)
            raw = raw.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(raw)
            return data.get("actores", [])
        except Exception:
            return []

    def _deduplicate(self, actores: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for a in actores:
            key = a.get("nombre", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(a)
        return unique

    def run(self, zona: str, nivel: str, sectores: list[str], progress_callback=None) -> list[dict]:
        raise NotImplementedError("Cada agente debe implementar run()")

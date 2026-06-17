import json
import re
import streamlit as st
from tools.search import search_web, format_results_for_llm
from tools.llm import get_llm_response


SYSTEM_PROMPT = """Eres un experto en análisis de ecosistemas territoriales.
Tu tarea es extraer información estructurada sobre actores de un ecosistema a partir de resultados de búsqueda web.
Siempre responde ÚNICAMENTE con JSON válido y estricto, sin texto adicional, sin markdown, sin explicaciones.
IMPORTANTE: No uses caracteres de escape innecesarios. Las URLs deben escribirse tal cual, sin barras invertidas."""

EXTRACTION_PROMPT = """A partir de los siguientes resultados de búsqueda sobre "{query}", extrae todos los actores relevantes.

Resultados:
{results}

Devuelve un JSON con esta estructura exacta (sin escape de caracteres, sin markdown):
{{
  "actores": [
    {{
      "nombre": "Nombre oficial de la organización",
      "tipo": "tipo específico (ej: empresa tecnológica, universidad pública, ONG ambiental...)",
      "descripcion": "Descripción breve de 1-2 frases de qué hace",
      "web": "https://ejemplo.com",
      "sector": "sector o área de actividad principal",
      "ubicacion": "ciudad o zona específica si se menciona",
      "contacto": "email o teléfono si aparece, sino dejar vacío"
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

    def _clean_json(self, raw: str) -> str:
        raw = re.sub(r"```json|```", "", raw).strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        raw = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'/', raw)
        return raw

    def _search_and_extract(self, query: str) -> list[dict]:
        results = search_web(query, max_results=8, tavily_key=self.tavily_key, serper_key=self.serper_key)
        if not results:
            return []

        formatted = format_results_for_llm(results)
        user_prompt = EXTRACTION_PROMPT.format(query=query, results=formatted)

        try:
            raw = get_llm_response(self.provider, self.api_key, SYSTEM_PROMPT, user_prompt)
            raw = self._clean_json(raw)
            data = json.loads(raw)
            return data.get("actores", [])
        except json.JSONDecodeError:
            try:
                data = json.loads(raw, strict=False)
                return data.get("actores", [])
            except Exception:
                return []
        except Exception as e:
            st.warning(f"Error LLM en '{query}': {str(e)}")
            return []

    def _run_queries(self, queries: list[str], categoria: str) -> list[dict]:
        todos = []
        for q in queries:
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = categoria
            todos.extend(actores)
        return self._deduplicate(todos)

    def _deduplicate(self, actores: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for a in actores:
            key = a.get("nombre", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(a)
        return unique

    def run(self, zona_info: dict, sectores: list[str], progress_callback=None) -> list[dict]:
        raise NotImplementedError("Cada agente debe implementar run()")

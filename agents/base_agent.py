import json
import re
import streamlit as st
from tools.search import search_web, format_results_for_llm
from tools.llm import get_llm_response

SYSTEM_PROMPT = """Eres un experto en análisis de ecosistemas territoriales.
Extrae información estructurada sobre actores a partir de resultados de búsqueda web.
Responde ÚNICAMENTE con JSON válido, sin texto adicional, sin markdown, sin explicaciones.
No uses caracteres de escape innecesarios. URLs sin barras invertidas."""

EXTRACTION_PROMPT = """Resultados de búsqueda sobre "{query}":

{results}

Extrae TODOS los actores identificables. Para empresas indica si es startup, pyme, multinacional, cooperativa o autónomo cuando puedas inferirlo.
Para academia indica si es universidad, máster, doctorado, FP, instituto u otro centro.

JSON con esta estructura exacta:
{{
  "actores": [
    {{
      "nombre": "Nombre oficial",
      "tipo": "tipo específico (startup, pyme, universidad pública, ONG...)",
      "descripcion": "Qué hace en 1-2 frases",
      "web": "https://url.com o vacío",
      "sector": "sector principal",
      "ubicacion": "zona específica si se menciona",
      "contacto": "email o teléfono si aparece"
    }}
  ]
}}

Si no hay actores claramente identificados devuelve {{"actores": []}}"""


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
        results = search_web(query, max_results=5, tavily_key=self.tavily_key, serper_key=self.serper_key)
        if not results:
            return []

        formatted = format_results_for_llm(results)
        user_prompt = EXTRACTION_PROMPT.format(query=query, results=formatted)

        try:
            raw = get_llm_response(self.provider, self.api_key, SYSTEM_PROMPT, user_prompt, use_large=False)
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

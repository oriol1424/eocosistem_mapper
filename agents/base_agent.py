import json
import re
import streamlit as st
from tools.search import search_web, format_results_for_llm
from tools.llm import get_llm_response

SYSTEM_PROMPT = """Eres un experto en análisis de ecosistemas territoriales locales.
Extrae información estructurada sobre actores a partir de resultados de búsqueda web.
Responde ÚNICAMENTE con JSON válido, sin texto adicional, sin markdown, sin explicaciones.
No uses caracteres de escape innecesarios."""

EXTRACTION_PROMPT = """Estás mapeando el ecosistema de: {zona_nombre}
País: {pais} | Región/Ciudad: {contexto} | Nivel: {nivel}

REGLA CRÍTICA DE UBICACIÓN: Solo extrae actores que estén CLARAMENTE ubicados en {zona_nombre} o en su municipio/ciudad inmediata ({contexto}).
- Si un actor menciona otra ciudad, región o país diferente → DESCÁRTALO
- Si la ubicación del actor es ambigua o no se menciona → DESCÁRTALO
- Si el nombre de la zona aparece como apellido de persona o nombre de otro lugar → DESCÁRTALO
- Prioriza actores con dirección, web o descripción que confirme su ubicación en {zona_nombre}

Resultados de búsqueda sobre "{query}":
{results}

Para empresas indica si es startup, pyme, multinacional, cooperativa o autónomo.
Para academia indica si es universidad, máster, doctorado, FP, instituto u otro centro.

JSON con esta estructura exacta:
{{
  "actores": [
    {{
      "nombre": "Nombre oficial",
      "tipo": "tipo específico",
      "descripcion": "Qué hace en 1-2 frases",
      "web": "https://url.com o vacío",
      "sector": "sector principal",
      "ubicacion": "dirección o zona específica confirmada",
      "contacto": "email o teléfono si aparece"
    }}
  ]
}}

Si no hay actores claramente ubicados en {zona_nombre} devuelve {{"actores": []}}"""


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

    def _search_and_extract(self, query: str, zona_info: dict) -> list[dict]:
        results = search_web(
            query, max_results=5,
            tavily_key=self.tavily_key,
            serper_key=self.serper_key,
            zona_info=zona_info
        )
        if not results:
            return []

        formatted = format_results_for_llm(results)
        user_prompt = EXTRACTION_PROMPT.format(
            zona_nombre=zona_info.get("nombre", ""),
            pais=zona_info.get("pais", ""),
            contexto=zona_info.get("contexto", "") or zona_info.get("nombre", ""),
            nivel=zona_info.get("nivel", ""),
            query=query,
            results=formatted
        )

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

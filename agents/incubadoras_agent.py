from agents.base_agent import BaseAgent

QUERIES_INCUBADORAS = {
    "es": [
        "incubadoras empresas {zona}",
        "aceleradoras startups {zona}",
        "vivero empresas {zona}",
        "espacio coworking innovación {zona}",
        "hub innovación emprendimiento {zona}",
        "programa aceleración empresas {zona}",
        "centro emprendimiento {zona}",
    ],
    "pt": [
        "incubadoras empresas {zona}",
        "aceleradoras startups {zona}",
        "parque tecnológico {zona}",
        "hub inovação {zona}",
    ],
    "fr": [
        "incubateurs entreprises {zona}",
        "accélérateurs startups {zona}",
        "pépinière entreprises {zona}",
        "hub innovation {zona}",
    ],
    "en": [
        "business incubators {zona}",
        "startup accelerators {zona}",
        "coworking innovation hub {zona}",
        "entrepreneurship center {zona}",
    ],
    "de": [
        "Gründerzentrum {zona}",
        "Startup Inkubator {zona}",
        "Technologiepark {zona}",
    ],
}

SYSTEM_PROMPT_INCUB = """Eres un experto en ecosistemas de innovación y emprendimiento.
Extrae información sobre incubadoras, aceleradoras y espacios de apoyo a startups.
Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown."""

EXTRACTION_PROMPT_INCUB = """Zona analizada: {zona_nombre} ({pais})

REGLA CRÍTICA: Solo extrae entidades claramente ubicadas en {zona_nombre} o su ciudad inmediata.
Descarta cualquier entidad de otra zona.

Resultados de búsqueda sobre "{query}":
{results}

Extrae incubadoras, aceleradoras, viveros de empresas, hubs de innovación y espacios de coworking orientados a startups.
Para cada una indica si es de titularidad pública o privada.

JSON exacto:
{{
  "actores": [
    {{
      "nombre": "Nombre oficial",
      "tipo": "incubadora / aceleradora / vivero / hub / coworking",
      "titularidad": "pública / privada / mixta",
      "sector": "tecnología / salud / general / otro sector",
      "descripcion": "Qué hace en 1-2 frases",
      "web": "https://url.com o vacío",
      "ubicacion": "dirección o zona confirmada",
      "contacto": "email o teléfono si aparece"
    }}
  ]
}}

Si no hay entidades claramente en {zona_nombre} devuelve {{"actores": []}}"""


class IncubadorasAgent(BaseAgent):

    def run(self, zona_info: dict, sectores: list[str] = None,
            progress_callback=None, log: list = None) -> list[dict]:
        from tools.search import search_web, format_results_for_llm
        from tools.llm import get_llm_response
        import json, re

        idioma = zona_info.get("idioma", "es")
        if idioma not in QUERIES_INCUBADORAS:
            idioma = "en"

        nombre = zona_info.get("nombre", "")
        queries = [q.format(zona=nombre) for q in QUERIES_INCUBADORAS[idioma]]

        todos = []
        for q in queries:
            if progress_callback:
                progress_callback(q)

            results = search_web(q, max_results=5,
                                 tavily_key=self.tavily_key,
                                 serper_key=self.serper_key,
                                 zona_info=zona_info)

            entrada_log = {
                "categoria": "Incubadoras y aceleradoras",
                "query": q,
                "resultados_web": len(results),
                "actores_extraidos": 0,
                "timestamp": __import__("datetime").datetime.now().strftime("%H:%M:%S"),
                "estado": "ok"
            }

            if not results:
                entrada_log["estado"] = "sin resultados"
                if log is not None:
                    log.append(entrada_log)
                continue

            formatted = format_results_for_llm(results)
            user_prompt = EXTRACTION_PROMPT_INCUB.format(
                zona_nombre=nombre,
                pais=zona_info.get("pais", ""),
                query=q,
                results=formatted
            )

            try:
                raw = get_llm_response(self.provider, self.api_key,
                                       SYSTEM_PROMPT_INCUB, user_prompt, use_large=False)
                raw = re.sub(r"```json|```", "", raw).strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]
                raw = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'/', raw)
                data = json.loads(raw)
                actores = data.get("actores", [])
                for a in actores:
                    a["categoria"] = "Incubadoras y aceleradoras"
                entrada_log["actores_extraidos"] = len(actores)
                todos.extend(actores)
            except Exception as e:
                entrada_log["estado"] = f"error: {str(e)[:50]}"

            if log is not None:
                log.append(entrada_log)

        return self._deduplicate(todos)

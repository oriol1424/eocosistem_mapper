import json
import re
from tools.llm import get_llm_response

CATEGORIAS = [
    "Empresas privadas",
    "Academia",
    "Administración pública",
    "Sociedad civil organizada",
]

SYSTEM_PROMPT = """Eres un experto en clasificación de actores de ecosistemas territoriales.
Tu tarea es revisar listas de actores y detectar los que están mal clasificados.
Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown."""

COORDINATION_PROMPT = """Revisa estos actores encontrados por categoría y detecta los que están mal clasificados.

{actores_json}

Reglas:
- Empresas privadas: organizaciones con ánimo de lucro (startups, pymes, multinacionales, cooperativas de trabajo)
- Academia: universidades, centros de investigación, escuelas, FP, másteres, doctorados
- Administración pública: ayuntamientos, organismos públicos, empresas públicas, servicios públicos
- Sociedad civil organizada: ONGs, asociaciones vecinales, fundaciones sin ánimo de lucro, colectivos

Devuelve JSON con los actores que deben moverse de categoría:
{{
  "mover": [
    {{
      "nombre": "nombre exacto del actor",
      "de": "categoría actual",
      "a": "categoría correcta",
      "razon": "motivo breve"
    }}
  ]
}}

Si todo está bien clasificado devuelve {{"mover": []}}"""


def coordinar(resultados: dict, provider: str, api_key: str) -> dict:
    """
    Revisa los resultados de todos los agentes y mueve actores mal clasificados.
    Devuelve el diccionario de resultados corregido.
    """
    resumen = {}
    for cat, actores in resultados.items():
        resumen[cat] = [
            {"nombre": a.get("nombre", ""), "tipo": a.get("tipo", ""), "descripcion": a.get("descripcion", "")}
            for a in actores[:30]
        ]

    try:
        user_prompt = COORDINATION_PROMPT.format(actores_json=json.dumps(resumen, ensure_ascii=False, indent=2))
        raw = get_llm_response(provider, api_key, SYSTEM_PROMPT, user_prompt, use_large=True)
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        movimientos = data.get("mover", [])
    except Exception:
        return resultados

    for mov in movimientos:
        nombre = mov.get("nombre", "").lower().strip()
        cat_origen = mov.get("de", "")
        cat_destino = mov.get("a", "")

        if cat_origen not in resultados or cat_destino not in resultados:
            continue

        actor_encontrado = None
        for actor in resultados[cat_origen]:
            if actor.get("nombre", "").lower().strip() == nombre:
                actor_encontrado = actor
                break

        if actor_encontrado:
            resultados[cat_origen].remove(actor_encontrado)
            actor_encontrado["categoria"] = cat_destino
            resultados[cat_destino].append(actor_encontrado)

    return resultados

from agents.base_agent import BaseAgent

SECTORES_DEFAULT = [
    "tecnología e innovación",
    "salud y farmacia",
    "industria y manufactura",
    "comercio y retail",
    "construcción e inmobiliaria",
    "servicios profesionales",
    "energía y medio ambiente",
    "turismo y hostelería",
    "alimentación y agroindustria",
    "finanzas y seguros"
]


class EmpresasAgent(BaseAgent):

    def run(self, zona: str, nivel: str, sectores: list[str], progress_callback=None) -> list[dict]:
        sectores_buscar = sectores if sectores else SECTORES_DEFAULT
        todos = []

        queries_generales = [
            f"empresas destacadas {zona}",
            f"principales empresas {zona} economia local",
            f"polígono industrial parque empresarial {zona}",
        ]

        for q in queries_generales:
            if progress_callback:
                progress_callback(f"Buscando: {q}")
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = "Empresas privadas"
            todos.extend(actores)

        for sector in sectores_buscar[:6]:
            q = f"empresas {sector} {zona}"
            if progress_callback:
                progress_callback(f"Sector {sector} en {zona}")
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = "Empresas privadas"
                if not a.get("sector"):
                    a["sector"] = sector
            todos.extend(actores)

        return self._deduplicate(todos)

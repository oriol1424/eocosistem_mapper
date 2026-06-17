from agents.base_agent import BaseAgent


class AdministracionAgent(BaseAgent):

    def run(self, zona: str, nivel: str, sectores: list[str], progress_callback=None) -> list[dict]:
        todos = []

        queries = [
            f"ayuntamiento municipio {zona}",
            f"diputación consell comarca {zona}",
            f"entidades públicas administración {zona}",
            f"empresa pública organismo público {zona}",
            f"servicios sociales públicos {zona}",
            f"agencia pública desarrollo económico {zona}",
        ]

        if nivel in ["Región", "País"]:
            queries.append(f"consejería gobierno autonómico {zona}")
            queries.append(f"delegación ministerio {zona}")

        for q in queries:
            if progress_callback:
                progress_callback(f"Buscando: {q}")
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = "Administración pública"
            todos.extend(actores)

        return self._deduplicate(todos)

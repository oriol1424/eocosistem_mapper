from agents.base_agent import BaseAgent


class SociedadAgent(BaseAgent):

    def run(self, zona: str, nivel: str, sectores: list[str], progress_callback=None) -> list[dict]:
        todos = []

        queries = [
            f"ONGs organizaciones no gubernamentales {zona}",
            f"asociaciones vecinales {zona}",
            f"fundaciones sociales {zona}",
            f"asociaciones culturales {zona}",
            f"cooperativas {zona}",
            f"colectivos sociales organizaciones ciudadanas {zona}",
        ]

        if sectores:
            for sector in sectores[:3]:
                queries.append(f"asociación organización {sector} {zona}")

        for q in queries:
            if progress_callback:
                progress_callback(f"Buscando: {q}")
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = "Sociedad civil organizada"
            todos.extend(actores)

        return self._deduplicate(todos)

from agents.base_agent import BaseAgent


class AcademiaAgent(BaseAgent):

    def run(self, zona: str, nivel: str, sectores: list[str], progress_callback=None) -> list[dict]:
        todos = []

        queries = [
            f"universidades {zona}",
            f"centros de investigación I+D {zona}",
            f"ciclos formativos FP formación profesional {zona}",
            f"escuelas colegios institutos públicos {zona}",
            f"centros tecnológicos innovación {zona}",
        ]

        if sectores:
            for sector in sectores[:3]:
                queries.append(f"formación educación {sector} {zona}")

        for q in queries:
            if progress_callback:
                progress_callback(f"Buscando: {q}")
            actores = self._search_and_extract(q)
            for a in actores:
                a["categoria"] = "Academia"
            todos.extend(actores)

        return self._deduplicate(todos)

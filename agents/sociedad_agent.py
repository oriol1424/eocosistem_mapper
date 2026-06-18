from agents.base_agent import BaseAgent
from tools.geo import get_queries

class SociedadAgent(BaseAgent):
    def run(self, zona_info: dict, sectores: list[str], progress_callback=None) -> list[dict]:
        queries = get_queries("sociedad", zona_info, sectores)
        todos = []
        for q in queries:
            if progress_callback:
                progress_callback(q)
            actores = self._search_and_extract(q, zona_info)
            for a in actores:
                a["categoria"] = "Sociedad civil organizada"
            todos.extend(actores)
        return self._deduplicate(todos)

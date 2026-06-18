from agents.base_agent import BaseAgent
from tools.geo import get_queries

class EmpresasAgent(BaseAgent):
    def run(self, zona_info: dict, sectores: list[str], progress_callback=None, log: list = None) -> list[dict]:
        queries = get_queries("empresas", zona_info, sectores)
        todos = []
        for q in queries:
            if progress_callback:
                progress_callback(q)
            actores = self._search_and_extract(q, zona_info, log=log)
            for a in actores:
                a["categoria"] = "Empresas privadas"
            todos.extend(actores)
        return self._deduplicate(todos)

"""
Composition root: conecta os adapters concretos aos ports e monta o grafo do agente
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importado antes dos adapters de proposito: e este import que carrega o .env,
# e os adapters leem OPENROUTER_MODEL/OPENROUTER_API_KEY ja na construcao.
import shared.settings  # noqa: F401

from adapters.chromadb_adapter import ChromaDBAdapter
from adapters.openrouter_adapter import OpenRouterAdapter
from graph.agent_graph import build_agent_graph
from graph.tools.rag_tool import build_search_tourist_spots_tool

_agent_graph = None


def get_agent_graph():
    """Constroi o grafo do agente com os adapters padrao na primeira chamada, reutiliza depois"""
    global _agent_graph
    if _agent_graph is None:
        llm = OpenRouterAdapter()
        vector_store = ChromaDBAdapter()
        tools = [build_search_tourist_spots_tool(vector_store)]
        _agent_graph = build_agent_graph(llm, tools)
    return _agent_graph

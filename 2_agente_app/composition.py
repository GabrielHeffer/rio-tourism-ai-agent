"""
Composition root: conecta os adapters concretos aos ports e monta o grafo do agente
"""

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importado antes dos adapters de proposito: e este import que carrega o .env,
# e os adapters leem OPENROUTER_MODEL/OPENROUTER_API_KEY ja na construcao.
import shared.settings  # noqa: F401
from shared.settings import resolve_agent_memory_path

from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from adapters.chromadb_adapter import ChromaDBAdapter
from adapters.openrouter_adapter import OpenRouterAdapter
from adapters.tavily_adapter import TavilyAdapter
from graph.agent_graph import build_agent_graph
from graph.prompts import TOURISM_AGENT_SYSTEM_PROMPT
from graph.tools.rag_tool import build_search_tourist_spots_tool
from graph.tools.web_search_tool import build_search_web_tool
from ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

_agent_graph = None
_checkpointer: Optional[BaseCheckpointSaver] = None


def build_checkpointer(memory_path: Optional[Path] = None) -> SqliteSaver:
    """Cria o checkpointer SQLite que guarda o historico de cada conversa (thread_id).

    check_same_thread=False e necessario porque o ToolNode executa as tools em
    threads; o SqliteSaver ja serializa o acesso a conexao com uma trava propria.
    """
    memory_path = memory_path or resolve_agent_memory_path()
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(memory_path), check_same_thread=False)
    return SqliteSaver(connection)


def get_checkpointer() -> BaseCheckpointSaver:
    """Cria o checkpointer na primeira chamada e reutiliza depois"""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = build_checkpointer()
    return _checkpointer


def build_tools(vector_store: VectorStorePort) -> List[BaseTool]:
    """Monta as tools do agente: a busca na base sempre; a busca na web so com TAVILY_API_KEY.

    A busca na web e opcional: sem a chave o agente funciona normalmente, so com a base.
    """
    tools = [build_search_tourist_spots_tool(vector_store)]

    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY nao configurada: agente sem busca na web")
        return tools

    tools.append(build_search_web_tool(TavilyAdapter()))
    return tools


def get_agent_graph():
    """Constroi o grafo do agente com os adapters padrao na primeira chamada, reutiliza depois"""
    global _agent_graph
    if _agent_graph is None:
        llm = OpenRouterAdapter()
        vector_store = ChromaDBAdapter()
        tools = build_tools(vector_store)
        _agent_graph = build_agent_graph(
            llm,
            tools,
            system_prompt=TOURISM_AGENT_SYSTEM_PROMPT,
            checkpointer=get_checkpointer(),
        )
    return _agent_graph


def delete_conversation(thread_id: str) -> None:
    """Apaga todo o historico salvo de uma conversa (direito de exclusao de dados pessoais)"""
    get_checkpointer().delete_thread(thread_id)

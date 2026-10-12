"""
Testes unitarios para composition.py (composition root)

Requer: chromadb instalado (composition.py importa ChromaDBAdapter, que
depende de shared/vector_store.py)
"""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from graph.prompts import TOURISM_AGENT_SYSTEM_PROMPT

try:
    import composition
    from langgraph.checkpoint.sqlite import SqliteSaver
    COMPOSITION_AVAILABLE = True
except ImportError:
    COMPOSITION_AVAILABLE = False

pytestmark = pytest.mark.skipif(not COMPOSITION_AVAILABLE, reason="chromadb nao instalado")


def save_two_messages(checkpointer, thread_id: str) -> None:
    """Grava uma troca de mensagens na conversa usando um grafo minimo com o checkpointer"""
    from langgraph.graph import START, END, StateGraph
    from graph.state import AgentState

    builder = StateGraph(AgentState)
    builder.add_node("echo", lambda state: {"messages": [AIMessage(content="resposta")]})
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    graph = builder.compile(checkpointer=checkpointer)
    graph.invoke(
        {"messages": [HumanMessage(content="pergunta")]},
        {"configurable": {"thread_id": thread_id}},
    )


def read_saved_messages(checkpointer, thread_id: str) -> list:
    """Le as mensagens salvas de uma conversa direto do checkpointer"""
    saved = checkpointer.get_tuple({"configurable": {"thread_id": thread_id}})
    if saved is None:
        return []
    return saved.checkpoint["channel_values"].get("messages", [])


class TestGetAgentGraph:
    """Testes para get_agent_graph"""

    def setup_method(self):
        """Reseta o cache de modulo entre testes"""
        composition._agent_graph = None

    def teardown_method(self):
        composition._agent_graph = None

    @patch("composition.get_checkpointer")
    @patch("composition.build_tools")
    @patch("composition.build_agent_graph")
    @patch("composition.ChromaDBAdapter")
    @patch("composition.OpenRouterAdapter")
    def test_builds_graph_with_default_adapters(
        self, mock_openrouter, mock_chromadb, mock_build_agent_graph, mock_build_tools, mock_get_checkpointer
    ):
        """Constroi os adapters, as tools e o grafo com prompt de sistema e checkpointer"""
        mock_build_agent_graph.return_value = Mock()

        graph = composition.get_agent_graph()

        mock_openrouter.assert_called_once_with()
        mock_chromadb.assert_called_once_with()
        mock_build_tools.assert_called_once_with(mock_chromadb.return_value)
        mock_build_agent_graph.assert_called_once_with(
            mock_openrouter.return_value,
            mock_build_tools.return_value,
            system_prompt=TOURISM_AGENT_SYSTEM_PROMPT,
            checkpointer=mock_get_checkpointer.return_value,
        )
        assert graph is mock_build_agent_graph.return_value

    @patch("composition.get_checkpointer")
    @patch("composition.build_tools")
    @patch("composition.build_agent_graph")
    @patch("composition.ChromaDBAdapter")
    @patch("composition.OpenRouterAdapter")
    def test_second_call_reuses_cached_graph(
        self, mock_openrouter, mock_chromadb, mock_build_agent_graph, mock_build_tools, mock_get_checkpointer
    ):
        """A segunda chamada nao reconstroi nada, reaproveita o grafo ja montado"""
        mock_build_agent_graph.return_value = Mock()

        first_graph = composition.get_agent_graph()
        second_graph = composition.get_agent_graph()

        assert first_graph is second_graph
        mock_openrouter.assert_called_once()
        mock_build_agent_graph.assert_called_once()


class TestBuildTools:
    """A busca na web e opcional: so entra com TAVILY_API_KEY configurada"""

    @patch("composition.TavilyAdapter")
    def test_with_tavily_key_registers_rag_and_web_tools(self, mock_tavily, monkeypatch):
        """Com a chave, o agente tem a busca na base e a busca na web"""
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-chave-de-teste")

        tools = composition.build_tools(Mock())

        assert [tool.name for tool in tools] == ["search_tourist_spots", "search_web"]
        mock_tavily.assert_called_once_with()

    @patch("composition.TavilyAdapter")
    def test_without_tavily_key_registers_only_rag_tool(self, mock_tavily, monkeypatch):
        """Sem a chave, o agente sobe so com a busca na base, sem erro"""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        tools = composition.build_tools(Mock())

        assert [tool.name for tool in tools] == ["search_tourist_spots"]
        mock_tavily.assert_not_called()


class TestBuildCheckpointer:
    """Testes para o checkpointer SQLite da memoria de conversa"""

    def test_creates_sqlite_file_and_returns_sqlite_saver(self, tmp_path):
        """O checkpointer e um SqliteSaver gravando no caminho informado"""
        memory_path = tmp_path / "memoria" / "agent_memory.sqlite"

        checkpointer = composition.build_checkpointer(memory_path)

        assert isinstance(checkpointer, SqliteSaver)
        assert memory_path.exists()

    def test_conversation_survives_reopening_the_file(self, tmp_path):
        """Uma conversa salva e lida por outro checkpointer no mesmo arquivo (simula reiniciar o programa)"""
        memory_path = tmp_path / "agent_memory.sqlite"
        save_two_messages(composition.build_checkpointer(memory_path), "conversa-1")

        reopened_checkpointer = composition.build_checkpointer(memory_path)
        saved_messages = read_saved_messages(reopened_checkpointer, "conversa-1")

        assert [message.content for message in saved_messages] == ["pergunta", "resposta"]

    def test_uses_agent_memory_path_from_environment(self, tmp_path, monkeypatch):
        """Sem caminho explicito, usa AGENT_MEMORY_PATH"""
        memory_path = tmp_path / "do_ambiente.sqlite"
        monkeypatch.setenv("AGENT_MEMORY_PATH", str(memory_path))

        composition.build_checkpointer()

        assert memory_path.exists()


class TestDeleteConversation:
    """Testes para delete_conversation"""

    def teardown_method(self):
        composition._checkpointer = None

    def test_deletes_only_the_given_conversation(self, tmp_path):
        """Apagar uma conversa remove o historico dela e preserva as outras"""
        checkpointer = composition.build_checkpointer(tmp_path / "agent_memory.sqlite")
        composition._checkpointer = checkpointer
        save_two_messages(checkpointer, "apagar")
        save_two_messages(checkpointer, "manter")

        composition.delete_conversation("apagar")

        assert read_saved_messages(checkpointer, "apagar") == []
        assert len(read_saved_messages(checkpointer, "manter")) == 2

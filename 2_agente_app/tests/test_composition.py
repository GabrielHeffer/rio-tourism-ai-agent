"""
Testes unitarios para composition.py (composition root)

Requer: chromadb instalado (composition.py importa ChromaDBAdapter, que
depende de shared/vector_store.py)
"""

from unittest.mock import Mock, patch

import pytest

try:
    import composition
    COMPOSITION_AVAILABLE = True
except ImportError:
    COMPOSITION_AVAILABLE = False

pytestmark = pytest.mark.skipif(not COMPOSITION_AVAILABLE, reason="chromadb nao instalado")


class TestGetAgentGraph:
    """Testes para get_agent_graph"""

    def setup_method(self):
        """Reseta o cache de modulo entre testes"""
        composition._agent_graph = None

    def teardown_method(self):
        composition._agent_graph = None

    @patch("composition.build_search_tourist_spots_tool")
    @patch("composition.build_agent_graph")
    @patch("composition.ChromaDBAdapter")
    @patch("composition.OpenRouterAdapter")
    def test_builds_graph_with_default_adapters(
        self, mock_openrouter, mock_chromadb, mock_build_agent_graph, mock_build_tool
    ):
        """Constroi OpenRouterAdapter, ChromaDBAdapter, a tool de RAG e o grafo"""
        mock_build_agent_graph.return_value = Mock()

        graph = composition.get_agent_graph()

        mock_openrouter.assert_called_once_with()
        mock_chromadb.assert_called_once_with()
        mock_build_tool.assert_called_once_with(mock_chromadb.return_value)
        mock_build_agent_graph.assert_called_once_with(
            mock_openrouter.return_value, [mock_build_tool.return_value]
        )
        assert graph is mock_build_agent_graph.return_value

    @patch("composition.build_search_tourist_spots_tool")
    @patch("composition.build_agent_graph")
    @patch("composition.ChromaDBAdapter")
    @patch("composition.OpenRouterAdapter")
    def test_second_call_reuses_cached_graph(
        self, mock_openrouter, mock_chromadb, mock_build_agent_graph, mock_build_tool
    ):
        """A segunda chamada nao reconstroi nada, reaproveita o grafo ja montado"""
        mock_build_agent_graph.return_value = Mock()

        first_graph = composition.get_agent_graph()
        second_graph = composition.get_agent_graph()

        assert first_graph is second_graph
        mock_openrouter.assert_called_once()
        mock_build_agent_graph.assert_called_once()

"""
Testes unitarios para adapters/tavily_adapter.py (nenhum teste chama a API real)

Requer: tavily-python instalado (pip install tavily-python)
"""

from unittest.mock import patch

import pytest

from domain.web_result import WebResult

try:
    from adapters.tavily_adapter import SEARCH_DEPTH, TavilyAdapter
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TAVILY_AVAILABLE, reason="tavily-python nao instalado")


def build_tavily_response() -> dict:
    """Resposta no formato devolvido por TavilyClient.search"""
    return {
        "query": "shows Rio de Janeiro",
        "results": [
            {
                "title": "Agenda de shows no Rio",
                "url": "https://exemplo.com/agenda",
                "content": "Show de samba no sabado na Lapa.",
                "published_date": "2026-10-10",
                "score": 0.9,
            },
            {
                "title": "Pagina sem data",
                "url": "https://exemplo.com/sem-data",
                "content": "Conteudo sem data de publicacao.",
            },
        ],
    }


class TestTavilyAdapterConstructor:
    """Testes para a configuracao da chave no construtor"""

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_reads_api_key_from_environment(self, mock_client, monkeypatch):
        """Sem chave explicita, usa TAVILY_API_KEY"""
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-chave-de-teste")

        TavilyAdapter()

        mock_client.assert_called_once_with(api_key="tvly-chave-de-teste")

    def test_missing_api_key_raises_value_error(self, monkeypatch):
        """Sem chave nenhuma, falha na construcao em vez de falhar na primeira busca"""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        with pytest.raises(ValueError):
            TavilyAdapter()


class TestTavilyAdapterSearch:
    """Testes para a busca e a conversao da resposta"""

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_converts_response_to_web_results(self, mock_client):
        """Cada resultado da API vira um WebResult com titulo, URL, trecho e data"""
        mock_client.return_value.search.return_value = build_tavily_response()

        results = TavilyAdapter(api_key="tvly-teste").search("shows Rio de Janeiro")

        assert results[0] == WebResult(
            title="Agenda de shows no Rio",
            url="https://exemplo.com/agenda",
            content="Show de samba no sabado na Lapa.",
            published_date="2026-10-10",
        )

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_missing_fields_become_empty_strings(self, mock_client):
        """Campo ausente na resposta vira string vazia, nunca None"""
        mock_client.return_value.search.return_value = build_tavily_response()

        results = TavilyAdapter(api_key="tvly-teste").search("shows Rio de Janeiro")

        assert results[1].published_date == ""

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_uses_basic_depth_and_requested_max_results(self, mock_client):
        """A busca usa profundidade basica (economiza creditos) e o limite pedido"""
        mock_client.return_value.search.return_value = {"results": []}

        TavilyAdapter(api_key="tvly-teste").search("museus Rio de Janeiro", max_results=3)

        mock_client.return_value.search.assert_called_once_with(
            query="museus Rio de Janeiro", max_results=3, search_depth=SEARCH_DEPTH
        )
        assert SEARCH_DEPTH == "basic"

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_logs_each_web_search(self, mock_client, caplog):
        """Cada busca aparece no log (o SDK do Tavily nao loga nada sozinho)"""
        mock_client.return_value.search.return_value = {"results": []}

        with caplog.at_level("INFO", logger="adapters.tavily_adapter"):
            TavilyAdapter(api_key="tvly-teste").search("samba Lapa Rio de Janeiro")

        assert "Buscando na web por: 'samba Lapa Rio de Janeiro'" in caplog.text

    @patch("adapters.tavily_adapter.TavilyClient")
    def test_api_error_returns_empty_list(self, mock_client):
        """Falha da API nao derruba a conversa: devolve lista vazia"""
        mock_client.return_value.search.side_effect = RuntimeError("limite de creditos")

        results = TavilyAdapter(api_key="tvly-teste").search("shows Rio de Janeiro")

        assert results == []

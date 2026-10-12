"""
Testes unitarios para graph/tools/web_search_tool.py (tool de busca na web)
"""

from typing import List

from langchain_core.tools import StructuredTool

from domain.web_result import WebResult
from graph.tools.web_search_tool import (
    EXTERNAL_CONTENT_NOTICE,
    MAX_CONTENT_CHARS,
    build_search_web_tool,
)
from ports.web_search_port import WebSearchPort


class FakeWebSearchPort(WebSearchPort):
    """Fake de teste para WebSearchPort, registra a ultima query recebida"""

    def __init__(self, results: List[WebResult]):
        self._results = results
        self.last_query = None

    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        self.last_query = query
        return self._results


def build_agenda_result(content: str = "Show de samba no sabado na Lapa.") -> WebResult:
    return WebResult(
        title="Agenda de shows no Rio",
        url="https://exemplo.com/agenda",
        content=content,
        published_date="2026-10-10",
    )


class TestBuildSearchWebTool:
    """Testes para build_search_web_tool"""

    def test_returns_structured_tool_named_search_web(self):
        """A tool tem o nome que o LLM usa para chama-la"""
        tool = build_search_web_tool(FakeWebSearchPort([]))

        assert isinstance(tool, StructuredTool)
        assert tool.name == "search_web"

    def test_query_reaches_the_port(self):
        """A query pedida pelo LLM chega ao port sem alteracao"""
        fake_port = FakeWebSearchPort([build_agenda_result()])
        tool = build_search_web_tool(fake_port)

        tool.invoke({"query": "shows Rio de Janeiro fim de semana"})

        assert fake_port.last_query == "shows Rio de Janeiro fim de semana"

    def test_output_marks_content_as_external(self):
        """O resultado vem com o aviso de conteudo externo (defesa contra prompt injection)"""
        tool = build_search_web_tool(FakeWebSearchPort([build_agenda_result()]))

        output = tool.invoke({"query": "shows Rio de Janeiro"})

        assert output.startswith(EXTERNAL_CONTENT_NOTICE)

    def test_output_includes_url_and_date(self):
        """Cada pagina traz a URL (para citar a fonte) e a data quando houver"""
        tool = build_search_web_tool(FakeWebSearchPort([build_agenda_result()]))

        output = tool.invoke({"query": "shows Rio de Janeiro"})

        assert "URL: https://exemplo.com/agenda" in output
        assert "Data: 2026-10-10" in output

    def test_long_content_is_truncated(self):
        """Trechos longos sao cortados para nao estourar o contexto do LLM"""
        long_content = "a" * (MAX_CONTENT_CHARS + 500)
        tool = build_search_web_tool(FakeWebSearchPort([build_agenda_result(long_content)]))

        output = tool.invoke({"query": "shows Rio de Janeiro"})

        assert "a" * MAX_CONTENT_CHARS in output
        assert "a" * (MAX_CONTENT_CHARS + 1) not in output

    def test_empty_results_return_friendly_message(self):
        """Sem resultados, devolve mensagem clara em vez de texto vazio"""
        tool = build_search_web_tool(FakeWebSearchPort([]))

        output = tool.invoke({"query": "algo inexistente Rio de Janeiro"})

        assert output == "Nenhum resultado encontrado na web para essa busca."

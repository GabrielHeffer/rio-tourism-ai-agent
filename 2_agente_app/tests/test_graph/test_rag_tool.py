"""
Testes unitarios para graph/tools.py (tool de RAG)
"""

from typing import List

from langchain_core.tools import StructuredTool

from domain.search_result import SearchResult
from domain.tourist_spot import TouristSpot
from ports.vector_store_port import VectorStorePort
from graph.tools.rag_tool import SearchTouristSpotsInput, build_search_tourist_spots_tool


class FakeVectorStorePort(VectorStorePort):
    """Fake de teste para VectorStorePort, sem depender de ChromaDB"""

    def __init__(self, results: List[SearchResult]):
        self._results = results

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        return self._results


def build_museu_naval_result() -> SearchResult:
    spot = TouristSpot(
        name="Museu Naval",
        category="cultura-arte",
        address="Rua Dom Manuel, 15 - Centro",
        phone="+55 21 2104-6851",
        hours="quinta a domingo, das 13h as 17h",
        website="",
        source_url="https://visit.rio/o-que-fazer/museu-naval/",
        source="riotur",
    )
    return SearchResult(spot=spot, document="Museu Naval e um ponto turistico no Rio de Janeiro.", distance=0.32)


class TestBuildSearchTouristSpotsTool:
    """Testes para build_search_tourist_spots_tool"""

    def test_returns_structured_tool(self):
        """A factory devolve uma StructuredTool"""
        tool = build_search_tourist_spots_tool(FakeVectorStorePort([]))

        assert isinstance(tool, StructuredTool)

    def test_tool_has_expected_name_and_schema(self):
        """Nome e schema de entrada da tool sao os esperados"""
        tool = build_search_tourist_spots_tool(FakeVectorStorePort([]))

        assert tool.name == "search_tourist_spots"
        assert tool.args_schema is SearchTouristSpotsInput

    def test_invoke_returns_spot_name_in_result(self):
        """Invocar a tool retorna texto contendo o nome do ponto turistico encontrado"""
        tool = build_search_tourist_spots_tool(FakeVectorStorePort([build_museu_naval_result()]))

        output = tool.invoke({"query": "museu no centro"})

        assert "Museu Naval" in output

    def test_invoke_includes_address_and_hours(self):
        """Texto formatado inclui endereco e horario do ponto turistico"""
        tool = build_search_tourist_spots_tool(FakeVectorStorePort([build_museu_naval_result()]))

        output = tool.invoke({"query": "museu no centro"})

        assert "Rua Dom Manuel, 15 - Centro" in output
        assert "quinta a domingo, das 13h as 17h" in output

    def test_invoke_with_no_results_returns_friendly_message(self):
        """Sem resultados, retorna mensagem amigavel em vez de texto vazio"""
        tool = build_search_tourist_spots_tool(FakeVectorStorePort([]))

        output = tool.invoke({"query": "algo que nao existe"})

        assert output == "Nenhum resultado encontrado para essa busca."

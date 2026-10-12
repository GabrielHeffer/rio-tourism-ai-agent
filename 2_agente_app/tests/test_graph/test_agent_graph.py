"""
Testes unitarios para graph/agent_graph.py (loop de tool-calling do agente)
"""

from typing import List

from langchain_core.messages import AIMessage, HumanMessage

from domain.search_result import SearchResult
from domain.tourist_spot import TouristSpot
from graph.agent_graph import build_agent_graph
from graph.tools.rag_tool import build_search_tourist_spots_tool
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort


class FakeLLMPort(LLMPort):
    """Fake de teste para LLMPort: devolve respostas pre-definidas em sequencia"""

    def __init__(self, responses: List[AIMessage]):
        self._responses = responses
        self.call_count = 0

    def generate_response(self, messages, tools=None) -> AIMessage:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


class FakeVectorStorePort(VectorStorePort):
    """Fake de teste para VectorStorePort, registra a ultima query recebida"""

    def __init__(self, results: List[SearchResult]):
        self._results = results
        self.last_query = None

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        self.last_query = query
        return self._results


def build_copacabana_result() -> SearchResult:
    spot = TouristSpot(
        name="Praia de Copacabana",
        category="praia",
        address="Av. Atlantica",
        phone="",
        hours="",
        website="",
        source_url="https://visit.rio/copacabana/",
        source="riotur",
    )
    return SearchResult(spot=spot, document="Praia famosa no Rio de Janeiro.", distance=0.2)


class TestBuildAgentGraph:
    """Testes para build_agent_graph"""

    def test_answers_directly_when_no_tool_call_is_needed(self):
        """Sem tool_calls na resposta do LLM, o grafo vai direto para END"""
        llm = FakeLLMPort([AIMessage(content="Ola! Bem-vindo ao Rio de Janeiro.")])
        tools = [build_search_tourist_spots_tool(FakeVectorStorePort([]))]
        graph = build_agent_graph(llm, tools)

        result = graph.invoke({"messages": [HumanMessage(content="Oi")]})

        assert result["messages"][-1].content == "Ola! Bem-vindo ao Rio de Janeiro."
        assert llm.call_count == 1

    def test_runs_tool_call_loop_and_returns_final_answer(self):
        """Com tool_calls na primeira resposta, o grafo executa a tool e chama o LLM de novo"""
        fake_vector_store = FakeVectorStorePort([build_copacabana_result()])
        tools = [build_search_tourist_spots_tool(fake_vector_store)]
        llm = FakeLLMPort(
            [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "search_tourist_spots", "args": {"query": "praia"}, "id": "call_1"}],
                ),
                AIMessage(content="Recomendo a Praia de Copacabana."),
            ]
        )
        graph = build_agent_graph(llm, tools)

        result = graph.invoke({"messages": [HumanMessage(content="Onde ir na praia?")]})

        assert result["messages"][-1].content == "Recomendo a Praia de Copacabana."
        assert llm.call_count == 2
        assert fake_vector_store.last_query == "praia"

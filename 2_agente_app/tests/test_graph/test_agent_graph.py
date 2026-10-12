"""
Testes unitarios para graph/agent_graph.py (loop de tool-calling e memoria de conversa)
"""

from typing import List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from domain.search_result import SearchResult
from domain.tourist_spot import TouristSpot
from graph.agent_graph import build_agent_graph, select_recent_messages
from graph.tools.rag_tool import build_search_tourist_spots_tool
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort

SYSTEM_PROMPT = "Voce e um assistente de turismo de teste."


class FakeLLMPort(LLMPort):
    """Fake de teste para LLMPort: devolve respostas pre-definidas e registra o que recebeu"""

    def __init__(self, responses: List[AIMessage]):
        self._responses = responses
        self.call_count = 0
        self.received_messages: List[list] = []

    def generate_response(self, messages, tools=None) -> AIMessage:
        self.received_messages.append(list(messages))
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


def build_rag_tools() -> list:
    return [build_search_tourist_spots_tool(FakeVectorStorePort([]))]


def build_thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


class TestBuildAgentGraph:
    """Testes para build_agent_graph"""

    def test_answers_directly_when_no_tool_call_is_needed(self):
        """Sem tool_calls na resposta do LLM, o grafo vai direto para END"""
        llm = FakeLLMPort([AIMessage(content="Ola! Bem-vindo ao Rio de Janeiro.")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT)

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
        graph = build_agent_graph(llm, tools, SYSTEM_PROMPT)

        result = graph.invoke({"messages": [HumanMessage(content="Onde ir na praia?")]})

        assert result["messages"][-1].content == "Recomendo a Praia de Copacabana."
        assert llm.call_count == 2
        assert fake_vector_store.last_query == "praia"


class TestSystemPrompt:
    """O prompt de sistema vai para o LLM, mas nunca para o historico salvo"""

    def test_llm_receives_system_prompt_first(self):
        """A primeira mensagem enviada ao LLM e o prompt de sistema"""
        llm = FakeLLMPort([AIMessage(content="Oi!")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT)

        graph.invoke({"messages": [HumanMessage(content="Oi")]})

        first_message = llm.received_messages[0][0]
        assert isinstance(first_message, SystemMessage)
        assert first_message.content == SYSTEM_PROMPT

    def test_system_prompt_is_not_stored_in_state(self):
        """O estado salvo da conversa contem so as mensagens do usuario e do agente"""
        llm = FakeLLMPort([AIMessage(content="Oi!")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT, checkpointer=InMemorySaver())
        config = build_thread_config("conversa-1")

        graph.invoke({"messages": [HumanMessage(content="Oi")]}, config)

        saved_messages = graph.get_state(config).values["messages"]
        assert not any(isinstance(message, SystemMessage) for message in saved_messages)


class TestConversationMemory:
    """Memoria de curto prazo: historico salvo por thread_id no checkpointer"""

    def test_second_message_sees_first_exchange(self):
        """Com o mesmo thread_id, a segunda chamada ao LLM recebe a primeira pergunta e resposta"""
        llm = FakeLLMPort([AIMessage(content="Sugiro Ipanema."), AIMessage(content="Perto dali tem o Arpoador.")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT, checkpointer=InMemorySaver())
        config = build_thread_config("viagem")

        graph.invoke({"messages": [HumanMessage(content="Onde ver o por do sol?")]}, config)
        graph.invoke({"messages": [HumanMessage(content="E perto dali?")]}, config)

        second_call_contents = [message.content for message in llm.received_messages[1]]
        assert second_call_contents == [SYSTEM_PROMPT, "Onde ver o por do sol?", "Sugiro Ipanema.", "E perto dali?"]

    def test_different_threads_do_not_share_history(self):
        """Conversas com thread_id diferentes nao se misturam"""
        llm = FakeLLMPort([AIMessage(content="Resposta A."), AIMessage(content="Resposta B.")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT, checkpointer=InMemorySaver())

        graph.invoke({"messages": [HumanMessage(content="Pergunta A")]}, build_thread_config("a"))
        graph.invoke({"messages": [HumanMessage(content="Pergunta B")]}, build_thread_config("b"))

        second_call_contents = [message.content for message in llm.received_messages[1]]
        assert second_call_contents == [SYSTEM_PROMPT, "Pergunta B"]


class TestSelectRecentMessages:
    """Janela de mensagens enviada ao LLM"""

    def test_keeps_only_the_most_recent_messages(self):
        """Historico maior que a janela e cortado, mantendo as mensagens mais recentes"""
        history = []
        for turn in range(10):
            history.append(HumanMessage(content="pergunta {}".format(turn)))
            history.append(AIMessage(content="resposta {}".format(turn)))

        recent = select_recent_messages(history, max_messages=4)

        assert [message.content for message in recent] == ["pergunta 8", "resposta 8", "pergunta 9", "resposta 9"]

    def test_window_never_starts_on_orphan_tool_result(self):
        """O corte nunca deixa um resultado de busca sem o pedido correspondente"""
        history = [
            HumanMessage(content="pergunta antiga"),
            AIMessage(content="", tool_calls=[{"name": "search_tourist_spots", "args": {"query": "x"}, "id": "c1"}]),
            ToolMessage(content="resultado", tool_call_id="c1"),
            AIMessage(content="resposta antiga"),
            HumanMessage(content="pergunta nova"),
            AIMessage(content="resposta nova"),
        ]

        recent = select_recent_messages(history, max_messages=4)

        assert isinstance(recent[0], HumanMessage)
        assert [message.content for message in recent] == ["pergunta nova", "resposta nova"]

    def test_llm_receives_window_plus_system_prompt(self):
        """Numa conversa longa, o LLM recebe no maximo a janela mais o prompt de sistema"""
        replies = [AIMessage(content="resposta {}".format(turn)) for turn in range(6)]
        llm = FakeLLMPort(replies)
        graph = build_agent_graph(
            llm, build_rag_tools(), SYSTEM_PROMPT, checkpointer=InMemorySaver(), max_history_messages=4
        )
        config = build_thread_config("longa")

        for turn in range(6):
            graph.invoke({"messages": [HumanMessage(content="pergunta {}".format(turn))]}, config)

        last_call = llm.received_messages[-1]
        assert len(last_call) <= 4 + 1
        assert isinstance(last_call[1], HumanMessage)
        assert last_call[-1].content == "pergunta 5"

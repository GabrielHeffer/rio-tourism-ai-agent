"""
Testes unitarios para graph/agent_graph.py (loop de tool-calling e memoria de conversa)
"""

from datetime import date
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from domain.search_result import SearchResult
from domain.tourist_spot import TouristSpot
from domain.web_result import WebResult
from graph.agent_graph import TOOL_LIMIT_NOTICE, build_agent_graph, select_recent_messages
from graph.tools.rag_tool import build_search_tourist_spots_tool
from graph.tools.web_search_tool import build_search_web_tool
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort
from ports.web_search_port import WebSearchPort

SYSTEM_PROMPT = "Voce e um assistente de turismo de teste."


class FakeLLMPort(LLMPort):
    """Fake de teste para LLMPort: devolve respostas pre-definidas e registra o que recebeu"""

    def __init__(self, responses: List[AIMessage]):
        self._responses = responses
        self.call_count = 0
        self.received_messages: List[list] = []
        self.received_tools: List[Optional[list]] = []

    def generate_response(self, messages, tools=None) -> AIMessage:
        self.received_messages.append(list(messages))
        self.received_tools.append(tools)
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


class FakeWebSearchPort(WebSearchPort):
    """Fake de teste para WebSearchPort, devolve resultados fixos"""

    def __init__(self, results: List[WebResult]):
        self._results = results

    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        return self._results


class TestWebSearchInGraph:
    """O grafo executa a busca na web quando o LLM pede search_web"""

    def test_runs_web_search_and_returns_result_to_llm(self):
        """O LLM pede search_web, o ToolNode executa e o resultado volta para o LLM"""
        agenda = WebResult(
            title="Agenda de shows no Rio",
            url="https://exemplo.com/agenda",
            content="Show de samba no sabado na Lapa.",
            published_date="2026-10-10",
        )
        tools = build_rag_tools() + [build_search_web_tool(FakeWebSearchPort([agenda]))]
        llm = FakeLLMPort(
            [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "search_web", "args": {"query": "shows Rio de Janeiro"}, "id": "call_web"}],
                ),
                AIMessage(content="Tem samba no sabado na Lapa (fonte: https://exemplo.com/agenda)."),
            ]
        )
        graph = build_agent_graph(llm, tools, SYSTEM_PROMPT)

        result = graph.invoke({"messages": [HumanMessage(content="Tem show no fim de semana?")]})

        tool_message = llm.received_messages[1][-1]
        assert isinstance(tool_message, ToolMessage)
        assert "https://exemplo.com/agenda" in tool_message.content
        assert result["messages"][-1].content.startswith("Tem samba")


class TestSystemPrompt:
    """O prompt de sistema vai para o LLM, mas nunca para o historico salvo"""

    def test_llm_receives_system_prompt_first(self):
        """A primeira mensagem enviada ao LLM e o prompt de sistema"""
        llm = FakeLLMPort([AIMessage(content="Oi!")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT)

        graph.invoke({"messages": [HumanMessage(content="Oi")]})

        first_message = llm.received_messages[0][0]
        assert isinstance(first_message, SystemMessage)
        assert first_message.content.startswith(SYSTEM_PROMPT)

    def test_system_prompt_includes_current_date(self):
        """O LLM recebe a data de hoje por extenso, para resolver 'proximo sabado' e datas de eventos"""
        llm = FakeLLMPort([AIMessage(content="Oi!")])
        graph = build_agent_graph(
            llm, build_rag_tools(), SYSTEM_PROMPT, current_date_provider=lambda: date(2026, 10, 12)
        )

        graph.invoke({"messages": [HumanMessage(content="Tem show no sabado?")]})

        assert "segunda-feira, 12 de outubro de 2026" in llm.received_messages[0][0].content

    def test_date_is_recalculated_on_each_call(self):
        """Uma conversa retomada em outro dia recebe a data nova, nao a do inicio"""
        current_days = iter([date(2026, 10, 12), date(2026, 10, 13)])
        llm = FakeLLMPort([AIMessage(content="Oi!"), AIMessage(content="De novo!")])
        graph = build_agent_graph(
            llm,
            build_rag_tools(),
            SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
            current_date_provider=lambda: next(current_days),
        )
        config = build_thread_config("dois-dias")

        graph.invoke({"messages": [HumanMessage(content="Oi")]}, config)
        graph.invoke({"messages": [HumanMessage(content="Voltei")]}, config)

        assert "terça-feira, 13 de outubro de 2026" in llm.received_messages[1][0].content

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

        history_contents = [message.content for message in llm.received_messages[1][1:]]
        assert history_contents == ["Onde ver o por do sol?", "Sugiro Ipanema.", "E perto dali?"]

    def test_different_threads_do_not_share_history(self):
        """Conversas com thread_id diferentes nao se misturam"""
        llm = FakeLLMPort([AIMessage(content="Resposta A."), AIMessage(content="Resposta B.")])
        graph = build_agent_graph(llm, build_rag_tools(), SYSTEM_PROMPT, checkpointer=InMemorySaver())

        graph.invoke({"messages": [HumanMessage(content="Pergunta A")]}, build_thread_config("a"))
        graph.invoke({"messages": [HumanMessage(content="Pergunta B")]}, build_thread_config("b"))

        history_contents = [message.content for message in llm.received_messages[1][1:]]
        assert history_contents == ["Pergunta B"]


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

    def test_previous_turns_keep_only_question_and_final_answer(self):
        """Das trocas anteriores entram so pergunta e resposta final, sem as buscas"""
        history = [
            HumanMessage(content="pergunta antiga"),
            AIMessage(content="", tool_calls=[{"name": "search_tourist_spots", "args": {"query": "x"}, "id": "c1"}]),
            ToolMessage(content="resultado", tool_call_id="c1"),
            AIMessage(content="resposta antiga"),
            HumanMessage(content="pergunta nova"),
            AIMessage(content="resposta nova"),
        ]

        recent = select_recent_messages(history, max_messages=4)

        assert [message.content for message in recent] == [
            "pergunta antiga", "resposta antiga", "pergunta nova", "resposta nova"
        ]
        assert not any(isinstance(message, ToolMessage) for message in recent[:2])

    def test_old_tool_heavy_turns_do_not_push_out_the_start_of_the_conversation(self):
        """Regressao: buscas antigas nao ocupam a janela e o inicio da conversa continua visivel.

        Antes, uma primeira pergunta com 3 rodadas de busca ocupava 8 mensagens; poucas
        perguntas depois ela saia da janela e o agente esquecia o contexto (o casal, a
        festa) e chegou a negar uma recomendacao que ele mesmo tinha feito.
        """
        history = []
        for turn in range(5):
            history.append(HumanMessage(content="pergunta {}".format(turn)))
            for round_index in range(3):
                call_id = "c{}_{}".format(turn, round_index)
                history.append(AIMessage(content="", tool_calls=[{"name": "search_web", "args": {"query": "q"}, "id": call_id}]))
                history.append(ToolMessage(content="resultado", tool_call_id=call_id))
            history.append(AIMessage(content="resposta {}".format(turn)))
        history.append(HumanMessage(content="monta o roteiro"))

        recent = select_recent_messages(history, max_messages=20)

        assert recent[0].content == "pergunta 0"
        assert recent[-1].content == "monta o roteiro"

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

    def test_tool_heavy_current_turn_is_never_dropped(self):
        """Regressao: um turno com mais buscas do que a janela ainda envia a pergunta ao LLM.

        Antes, as ultimas N mensagens eram so pedidos e resultados de busca, o corte
        exigia comecar numa mensagem do usuario e descartava tudo: o LLM recebia so o
        prompt de sistema e respondia como se a conversa estivesse comecando.
        """
        history = [
            HumanMessage(content="turno antigo"),
            AIMessage(content="resposta antiga"),
            HumanMessage(content="Monta um roteiro de 2 dias"),
        ]
        for round_index, call_count in enumerate([5, 4, 5, 1, 5]):
            calls = [
                {"name": "search_web", "args": {"query": "q"}, "id": "c{}_{}".format(round_index, i)}
                for i in range(call_count)
            ]
            history.append(AIMessage(content="", tool_calls=calls))
            history.extend(ToolMessage(content="resultado", tool_call_id=call["id"]) for call in calls)

        recent = select_recent_messages(history, max_messages=20)

        assert recent[0].content == "Monta um roteiro de 2 dias"
        assert len(recent) == len(history) - 2

    def test_previous_turns_fill_the_remaining_budget(self):
        """Com o turno atual pequeno, as trocas anteriores completam a janela"""
        history = [
            HumanMessage(content="pergunta 1"),
            AIMessage(content="resposta 1"),
            HumanMessage(content="pergunta 2"),
            AIMessage(content="resposta 2"),
            HumanMessage(content="pergunta 3"),
        ]

        recent = select_recent_messages(history, max_messages=3)

        assert [message.content for message in recent] == ["pergunta 2", "resposta 2", "pergunta 3"]


def build_web_tool_call(round_index: int) -> AIMessage:
    """Resposta do LLM pedindo uma busca na web"""
    return AIMessage(
        content="",
        tool_calls=[{"name": "search_web", "args": {"query": "q"}, "id": "call_{}".format(round_index)}],
    )


class TestToolRoundLimit:
    """Limite de rodadas de busca por pergunta (protege creditos e evita loop)"""

    def build_graph_with_web(self, llm: FakeLLMPort, max_tool_rounds: int):
        tools = build_rag_tools() + [build_search_web_tool(FakeWebSearchPort([]))]
        return build_agent_graph(llm, tools, SYSTEM_PROMPT, max_tool_rounds=max_tool_rounds)

    def test_llm_is_called_without_tools_at_the_limit(self):
        """Depois de N rodadas, o LLM e chamado sem tools e com o aviso de limite"""
        llm = FakeLLMPort([build_web_tool_call(0), build_web_tool_call(1), AIMessage(content="Roteiro pronto.")])
        graph = self.build_graph_with_web(llm, max_tool_rounds=2)

        result = graph.invoke({"messages": [HumanMessage(content="Monta um roteiro")]})

        assert result["messages"][-1].content == "Roteiro pronto."
        assert llm.received_tools[0] is not None
        assert llm.received_tools[1] is not None
        assert llm.received_tools[2] is None
        assert TOOL_LIMIT_NOTICE in llm.received_messages[2][0].content

    def test_tool_request_at_the_limit_is_ignored(self):
        """Se o LLM ainda pedir tool no limite, o pedido e descartado e o grafo termina"""
        llm = FakeLLMPort([build_web_tool_call(0), AIMessage(content="Parcial.", tool_calls=build_web_tool_call(1).tool_calls)])
        graph = self.build_graph_with_web(llm, max_tool_rounds=1)

        result = graph.invoke({"messages": [HumanMessage(content="Monta um roteiro")]})

        final_message = result["messages"][-1]
        assert final_message.content == "Parcial."
        assert not final_message.tool_calls
        assert llm.call_count == 2

    def test_rounds_are_counted_per_question(self):
        """Buscas de perguntas anteriores nao contam para o limite da pergunta atual"""
        llm = FakeLLMPort(
            [build_web_tool_call(0), AIMessage(content="Resposta 1."), build_web_tool_call(1), AIMessage(content="Resposta 2.")]
        )
        tools = build_rag_tools() + [build_search_web_tool(FakeWebSearchPort([]))]
        graph = build_agent_graph(llm, tools, SYSTEM_PROMPT, checkpointer=InMemorySaver(), max_tool_rounds=1)
        config = build_thread_config("duas-perguntas")

        graph.invoke({"messages": [HumanMessage(content="Pergunta 1")]}, config)
        graph.invoke({"messages": [HumanMessage(content="Pergunta 2")]}, config)

        assert llm.received_tools[2] is not None

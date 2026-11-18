"""
Grafo do agente: loop de chamada ao LLM e execucao de tools

Memoria de curto prazo: quando compilado com um checkpointer, o LangGraph salva o
estado (historico de mensagens) ao fim de cada execucao e o recarrega na proxima
chamada com o mesmo thread_id. O checkpointer e injetado de fora (composition.py),
entao este modulo nao sabe se o historico vive em memoria ou em SQLite.
"""

from datetime import date
from typing import Callable, List, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from graph.prompts import build_current_date_context
from graph.state import AgentState
from ports.llm_port import LLMPort

# Quantas mensagens recentes o LLM recebe a cada chamada. O historico completo
# continua salvo no checkpointer; a janela so limita o custo e o tamanho do prompt.
# Das perguntas anteriores contam so pergunta + resposta (~10 trocas); a pergunta
# atual entra inteira, com as buscas.
MAX_HISTORY_MESSAGES = 20

# Quantas rodadas de busca o agente pode fazer para responder uma mesma pergunta.
# Sem limite, uma pergunta ampla ("monta um roteiro") chegou a 5 rodadas e ~15
# buscas na web, gastando creditos do Tavily e alongando a resposta.
MAX_TOOL_ROUNDS = 3

TOOL_LIMIT_NOTICE = (
    "Limite de buscas desta pergunta atingido: responda agora com as informações "
    "que você já tem, sem pedir novas buscas. Se faltar algo, diga o que faltou."
)


def find_last_human_index(messages: List[BaseMessage]) -> int:
    """Devolve o indice da ultima mensagem do usuario, ou -1 se nao houver"""
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return index
    return -1


def is_tool_exchange(message: BaseMessage) -> bool:
    """Diz se a mensagem e parte de uma busca: pedido de tool do LLM ou resultado da tool"""
    return isinstance(message, ToolMessage) or (isinstance(message, AIMessage) and bool(message.tool_calls))


def select_recent_messages(messages: List[BaseMessage], max_messages: int) -> List[BaseMessage]:
    """Seleciona as mensagens enviadas ao LLM: o turno atual inteiro mais as trocas anteriores que couberem.

    O turno atual (a ultima pergunta do usuario e todas as buscas feitas para
    responde-la) nunca e cortado: um turno com muitas buscas em paralelo passava
    sozinho da janela, o corte descartava a propria pergunta e o LLM ficava sem
    conversa nenhuma.

    Das trocas anteriores entram so a pergunta e a resposta final, sem as buscas:
    a resposta ja resume o que importava delas, e as buscas antigas ocupavam a
    janela a ponto de o agente esquecer o inicio da conversa (e ate "corrigir" uma
    recomendacao que ele mesmo tinha feito). O corte comeca sempre numa mensagem
    do usuario.
    """
    last_human_index = find_last_human_index(messages)
    if last_human_index < 0:
        return list(messages)

    current_turn = messages[last_human_index:]
    previous_budget = max_messages - len(current_turn)
    if previous_budget <= 0:
        return list(current_turn)

    previous_dialogue = [
        message for message in messages[:last_human_index] if not is_tool_exchange(message)
    ]
    previous_turns = trim_messages(
        previous_dialogue,
        strategy="last",
        token_counter=len,
        max_tokens=previous_budget,
        start_on="human",
    )
    return previous_turns + list(current_turn)


def count_tool_rounds_in_current_turn(messages: List[BaseMessage]) -> int:
    """Conta quantas vezes o LLM pediu tools desde a ultima pergunta do usuario"""
    current_turn = messages[find_last_human_index(messages) + 1:]
    return sum(1 for message in current_turn if isinstance(message, AIMessage) and message.tool_calls)


def build_agent_graph(
    llm: LLMPort,
    tools: List[BaseTool],
    system_prompt: str,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    max_history_messages: int = MAX_HISTORY_MESSAGES,
    current_date_provider: Callable[[], date] = date.today,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
) -> CompiledStateGraph:
    """Monta o grafo do agente: chama o LLM, executa tools quando pedido, repete ate ter resposta final.

    current_date_provider e injetavel para os testes fixarem a data.
    """

    def _call_agent(state: AgentState) -> dict:
        # O prompt de sistema entra so na chamada ao LLM e nunca no estado salvo:
        # assim ele nao se repete no historico e uma mudanca no prompt vale tambem
        # para conversas antigas. A data e recalculada a cada chamada porque uma
        # conversa retomada pode estar em outro dia.
        messages = state["messages"]
        system_content = "{}\n\n{}".format(
            system_prompt, build_current_date_context(current_date_provider())
        )

        # No limite de rodadas o LLM e chamado sem tools: so pode responder.
        is_tool_limit_reached = count_tool_rounds_in_current_turn(messages) >= max_tool_rounds
        if is_tool_limit_reached:
            system_content = "{}\n\n{}".format(system_content, TOOL_LIMIT_NOTICE)

        llm_input = [SystemMessage(content=system_content)] + select_recent_messages(
            messages, max_history_messages
        )
        response = llm.generate_response(llm_input, tools=None if is_tool_limit_reached else tools)

        # Defesa extra: mesmo sem tools disponiveis, um pedido de tool aqui faria o
        # grafo voltar ao no de tools e passar do limite.
        if is_tool_limit_reached and response.tool_calls:
            response = AIMessage(content=response.content or TOOL_LIMIT_NOTICE)
        return {"messages": [response]}

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("agent", _call_agent)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph_builder.add_edge("tools", "agent")

    return graph_builder.compile(checkpointer=checkpointer)

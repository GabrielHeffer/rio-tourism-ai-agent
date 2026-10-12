"""
Grafo do agente: loop de chamada ao LLM e execucao de tools

Memoria de curto prazo: quando compilado com um checkpointer, o LangGraph salva o
estado (historico de mensagens) ao fim de cada execucao e o recarrega na proxima
chamada com o mesmo thread_id. O checkpointer e injetado de fora (composition.py),
entao este modulo nao sabe se o historico vive em memoria ou em SQLite.
"""

from typing import List, Optional

from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from graph.state import AgentState
from ports.llm_port import LLMPort

# Quantas mensagens recentes o LLM recebe a cada chamada. O historico completo
# continua salvo no checkpointer; a janela so limita o custo e o tamanho do prompt.
# Conta tambem as mensagens das buscas (pedido de tool + resultado).
MAX_HISTORY_MESSAGES = 20


def select_recent_messages(messages: List[BaseMessage], max_messages: int) -> List[BaseMessage]:
    """Seleciona as mensagens mais recentes que cabem na janela enviada ao LLM.

    A janela sempre comeca numa mensagem do usuario: cortar no meio de uma busca
    deixaria um resultado de tool sem o pedido correspondente, e a API do modelo
    recusa esse historico.
    """
    return trim_messages(
        messages,
        strategy="last",
        token_counter=len,
        max_tokens=max_messages,
        start_on="human",
    )


def build_agent_graph(
    llm: LLMPort,
    tools: List[BaseTool],
    system_prompt: str,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    max_history_messages: int = MAX_HISTORY_MESSAGES,
) -> CompiledStateGraph:
    """Monta o grafo do agente: chama o LLM, executa tools quando pedido, repete ate ter resposta final"""

    def _call_agent(state: AgentState) -> dict:
        # O prompt de sistema entra so na chamada ao LLM e nunca no estado salvo:
        # assim ele nao se repete no historico e uma mudanca no prompt vale tambem
        # para conversas antigas.
        recent_messages = select_recent_messages(state["messages"], max_history_messages)
        llm_input = [SystemMessage(content=system_prompt)] + recent_messages
        response = llm.generate_response(llm_input, tools=tools)
        return {"messages": [response]}

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("agent", _call_agent)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph_builder.add_edge("tools", "agent")

    return graph_builder.compile(checkpointer=checkpointer)

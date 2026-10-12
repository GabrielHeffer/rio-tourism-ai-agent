"""
Grafo do agente: loop de chamada ao LLM e execucao de tools
"""

from typing import List

from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from graph.state import AgentState
from ports.llm_port import LLMPort


def build_agent_graph(llm: LLMPort, tools: List[BaseTool]) -> CompiledStateGraph:
    """Monta o grafo do agente: chama o LLM, executa tools quando pedido, repete ate ter resposta final"""

    def _call_agent(state: AgentState) -> dict:
        response = llm.generate_response(state["messages"], tools=tools)
        return {"messages": [response]}

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("agent", _call_agent)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", tools_condition, ["tools", END])
    graph_builder.add_edge("tools", "agent")

    return graph_builder.compile()

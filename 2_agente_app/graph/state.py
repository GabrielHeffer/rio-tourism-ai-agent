"""
Estado do grafo do agente
"""

from typing import Annotated, List

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Estado do grafo do agente: historico de mensagens da conversa"""

    messages: Annotated[List[BaseMessage], add_messages]

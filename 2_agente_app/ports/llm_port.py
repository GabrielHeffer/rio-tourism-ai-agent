"""
Porta (contrato) para geracao de respostas de um LLM
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool


class LLMPort(ABC):
    """Contrato para geracao de respostas de um LLM, com suporte a tool-calling"""

    @abstractmethod
    def generate_response(
        self, messages: List[BaseMessage], tools: Optional[List[BaseTool]] = None
    ) -> AIMessage:
        """Gera a proxima resposta do LLM a partir do historico, podendo incluir chamadas de tool"""
        raise NotImplementedError

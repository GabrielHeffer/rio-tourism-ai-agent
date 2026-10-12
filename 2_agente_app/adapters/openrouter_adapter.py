"""
Adapter que implementa LLMPort usando o OpenRouter (endpoint OpenAI-compatible)
"""

import os
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from ports.llm_port import LLMPort

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"


class OpenRouterAdapter(LLMPort):
    """Implementa LLMPort usando o OpenRouter (endpoint OpenAI-compatible)"""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self._client = ChatOpenAI(
            model=model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=OPENROUTER_BASE_URL,
        )

    def generate_response(
        self, messages: List[BaseMessage], tools: Optional[List[BaseTool]] = None
    ) -> AIMessage:
        """Gera a resposta, vinculando as tools na chamada quando fornecidas"""
        client = self._client.bind_tools(tools) if tools else self._client
        return client.invoke(messages)

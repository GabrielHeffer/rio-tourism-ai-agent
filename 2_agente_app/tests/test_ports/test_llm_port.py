"""
Testes unitarios para ports/llm_port.py
"""

from typing import List, Optional

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from ports.llm_port import LLMPort


class TestLLMPort:
    """Testes para o contrato LLMPort"""

    def test_cannot_instantiate_directly(self):
        """LLMPort e abstrata e nao pode ser instanciada diretamente"""
        with pytest.raises(TypeError):
            LLMPort()

    def test_subclass_without_generate_response_cannot_be_instantiated(self):
        """Subclasse que nao implementa generate_response tambem nao pode ser instanciada"""

        class IncompleteAdapter(LLMPort):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_implementing_generate_response_can_be_instantiated(self):
        """Subclasse que implementa generate_response instancia normalmente"""

        class FakeAdapter(LLMPort):
            def generate_response(
                self, messages: List[BaseMessage], tools: Optional[List[BaseTool]] = None
            ) -> AIMessage:
                return AIMessage(content="resposta fake")

        adapter = FakeAdapter()

        assert isinstance(adapter, LLMPort)
        assert adapter.generate_response([]).content == "resposta fake"

"""
Testes unitarios para main.py (recebimento de mensagem do usuario)

Requer: chromadb instalado (main.py importa composition.py, que importa
ChromaDBAdapter, que depende de shared/vector_store.py)
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from graph.prompts import TOURISM_AGENT_SYSTEM_PROMPT

try:
    import main
    MAIN_AVAILABLE = True
except ImportError:
    MAIN_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MAIN_AVAILABLE, reason="chromadb nao instalado")


class FakeCompiledGraph:
    """Fake de teste para o grafo compilado: registra o input e devolve uma resposta fixa"""

    def __init__(self, response_content: str):
        self.last_input = None
        self._response_content = response_content

    def invoke(self, input_):
        self.last_input = input_
        return {"messages": input_["messages"] + [AIMessage(content=self._response_content)]}


class TestHandleMessage:
    """Testes para handle_message"""

    def test_first_call_seeds_system_prompt(self, monkeypatch):
        """Sem history, a primeira mensagem inclui o SystemMessage de persona"""
        fake_graph = FakeCompiledGraph("Ola! Bem-vindo ao Rio.")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)

        result = main.handle_message("O que fazer no Rio?")

        assert result == "Ola! Bem-vindo ao Rio."
        seeded = fake_graph.last_input["messages"]
        assert isinstance(seeded[0], SystemMessage)
        assert seeded[0].content == TOURISM_AGENT_SYSTEM_PROMPT
        assert isinstance(seeded[-1], HumanMessage)
        assert seeded[-1].content == "O que fazer no Rio?"

    def test_reuses_provided_history_without_reseeding_system_prompt(self, monkeypatch):
        """Com history, a mensagem e apenas anexada, sem novo SystemMessage"""
        fake_graph = FakeCompiledGraph("Recomendo o Pao de Acucar.")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)
        history = [SystemMessage(content="prompt customizado"), HumanMessage(content="oi")]

        result = main.handle_message("e praias?", history=history)

        assert result == "Recomendo o Pao de Acucar."
        seeded = fake_graph.last_input["messages"]
        assert seeded[0].content == "prompt customizado"
        assert seeded[-1].content == "e praias?"

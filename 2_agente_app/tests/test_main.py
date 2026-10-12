"""
Testes unitarios para main.py (envio de mensagem para uma conversa)

Requer: chromadb instalado (main.py importa composition.py, que importa
ChromaDBAdapter, que depende de shared/vector_store.py)
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

try:
    import main
    MAIN_AVAILABLE = True
except ImportError:
    MAIN_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MAIN_AVAILABLE, reason="chromadb nao instalado")


class FakeCompiledGraph:
    """Fake de teste para o grafo compilado: registra input e config e devolve uma resposta fixa"""

    def __init__(self, response_content: str):
        self.last_input = None
        self.last_config = None
        self._response_content = response_content

    def invoke(self, input_, config=None):
        self.last_input = input_
        self.last_config = config
        return {"messages": input_["messages"] + [AIMessage(content=self._response_content)]}


class TestHandleMessage:
    """Testes para handle_message"""

    def test_returns_final_agent_answer(self, monkeypatch):
        """Devolve o conteudo da ultima mensagem do agente"""
        fake_graph = FakeCompiledGraph("Ola! Bem-vindo ao Rio.")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)

        answer = main.handle_message("O que fazer no Rio?", thread_id="conversa-1")

        assert answer == "Ola! Bem-vindo ao Rio."

    def test_sends_only_the_new_user_message(self, monkeypatch):
        """So a mensagem nova vai para o grafo: o historico vem do checkpointer"""
        fake_graph = FakeCompiledGraph("ok")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)

        main.handle_message("e praias?", thread_id="conversa-1")

        sent_messages = fake_graph.last_input["messages"]
        assert len(sent_messages) == 1
        assert isinstance(sent_messages[0], HumanMessage)
        assert sent_messages[0].content == "e praias?"

    def test_does_not_send_system_prompt(self, monkeypatch):
        """O prompt de sistema e responsabilidade do grafo, nao do entrypoint"""
        fake_graph = FakeCompiledGraph("ok")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)

        main.handle_message("Oi", thread_id="conversa-1")

        assert not any(isinstance(message, SystemMessage) for message in fake_graph.last_input["messages"])

    def test_passes_thread_id_in_config(self, monkeypatch):
        """O thread_id identifica a conversa no checkpointer"""
        fake_graph = FakeCompiledGraph("ok")
        monkeypatch.setattr(main, "get_agent_graph", lambda: fake_graph)

        main.handle_message("Oi", thread_id="viagem-avo")

        assert fake_graph.last_config == {"configurable": {"thread_id": "viagem-avo"}}

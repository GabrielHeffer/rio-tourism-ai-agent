"""
Testes unitarios para adapters/openrouter_adapter.py

Requer: langchain-openai instalado (pip install langchain-openai)
"""

from unittest.mock import Mock, patch

import pytest

try:
    from adapters.openrouter_adapter import DEFAULT_MODEL, OPENROUTER_BASE_URL, OpenRouterAdapter
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False

pytestmark = pytest.mark.skipif(not LANGCHAIN_OPENAI_AVAILABLE, reason="langchain_openai nao instalado")


class TestOpenRouterAdapterConstructor:
    """Testes para a configuracao do client no construtor"""

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_uses_default_model_when_not_specified(self, mock_chat_openai, monkeypatch):
        """Sem model explicito e sem OPENROUTER_MODEL, usa DEFAULT_MODEL"""
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

        OpenRouterAdapter(api_key="fake-key")

        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["model"] == DEFAULT_MODEL
        assert call_kwargs["base_url"] == OPENROUTER_BASE_URL

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_uses_openrouter_model_env_var(self, mock_chat_openai, monkeypatch):
        """OPENROUTER_MODEL sobrescreve o modelo padrao quando definido"""
        monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-5-nano")

        OpenRouterAdapter(api_key="fake-key")

        assert mock_chat_openai.call_args[1]["model"] == "openai/gpt-5-nano"

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_explicit_model_wins_over_env_var(self, mock_chat_openai, monkeypatch):
        """Model passado explicitamente tem prioridade sobre a env var"""
        monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-5-nano")

        OpenRouterAdapter(model="deepseek/deepseek-v4-flash-0731", api_key="fake-key")

        assert mock_chat_openai.call_args[1]["model"] == "deepseek/deepseek-v4-flash-0731"

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_uses_openrouter_api_key_env_var(self, mock_chat_openai, monkeypatch):
        """Sem api_key explicita, usa OPENROUTER_API_KEY"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")

        OpenRouterAdapter()

        assert mock_chat_openai.call_args[1]["api_key"] == "env-key"


class TestOpenRouterAdapterGenerateResponse:
    """Testes para generate_response"""

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_generate_response_without_tools_invokes_client_directly(self, mock_chat_openai):
        """Sem tools, chama self._client.invoke(messages) direto, sem bind_tools"""
        mock_client = Mock()
        mock_chat_openai.return_value = mock_client

        adapter = OpenRouterAdapter(api_key="fake-key")
        messages = [Mock()]
        result = adapter.generate_response(messages)

        mock_client.invoke.assert_called_once_with(messages)
        mock_client.bind_tools.assert_not_called()
        assert result is mock_client.invoke.return_value

    @patch("adapters.openrouter_adapter.ChatOpenAI")
    def test_generate_response_with_tools_binds_before_invoking(self, mock_chat_openai):
        """Com tools, vincula via bind_tools antes de invocar"""
        mock_client = Mock()
        mock_bound_client = Mock()
        mock_client.bind_tools.return_value = mock_bound_client
        mock_chat_openai.return_value = mock_client

        adapter = OpenRouterAdapter(api_key="fake-key")
        messages = [Mock()]
        tools = [Mock()]
        result = adapter.generate_response(messages, tools=tools)

        mock_client.bind_tools.assert_called_once_with(tools)
        mock_bound_client.invoke.assert_called_once_with(messages)
        assert result is mock_bound_client.invoke.return_value

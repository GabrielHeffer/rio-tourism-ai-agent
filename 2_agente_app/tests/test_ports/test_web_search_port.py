"""
Testes unitarios para ports/web_search_port.py
"""

from typing import List

import pytest

from domain.web_result import WebResult
from ports.web_search_port import WebSearchPort


class TestWebSearchPort:
    """Testes para o contrato WebSearchPort"""

    def test_cannot_instantiate_directly(self):
        """WebSearchPort e abstrata e nao pode ser instanciada diretamente"""
        with pytest.raises(TypeError):
            WebSearchPort()

    def test_subclass_without_search_cannot_be_instantiated(self):
        """Subclasse que nao implementa search tambem nao pode ser instanciada"""

        class IncompleteAdapter(WebSearchPort):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_implementing_search_can_be_instantiated(self):
        """Subclasse que implementa search instancia normalmente"""

        class FakeAdapter(WebSearchPort):
            def search(self, query: str, max_results: int = 5) -> List[WebResult]:
                return []

        assert isinstance(FakeAdapter(), WebSearchPort)

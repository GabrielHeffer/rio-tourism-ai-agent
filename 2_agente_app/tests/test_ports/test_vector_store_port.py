"""
Testes unitarios para ports/vector_store_port.py
"""

from typing import List

import pytest

from domain.search_result import SearchResult
from ports.vector_store_port import VectorStorePort


class TestVectorStorePort:
    """Testes para o contrato VectorStorePort"""

    def test_cannot_instantiate_directly(self):
        """VectorStorePort e abstrata e nao pode ser instanciada diretamente"""
        with pytest.raises(TypeError):
            VectorStorePort()

    def test_subclass_without_search_cannot_be_instantiated(self):
        """Subclasse que nao implementa search tambem nao pode ser instanciada"""

        class IncompleteAdapter(VectorStorePort):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_implementing_search_can_be_instantiated(self):
        """Subclasse que implementa search instancia normalmente"""

        class FakeAdapter(VectorStorePort):
            def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
                return []

        adapter = FakeAdapter()

        assert isinstance(adapter, VectorStorePort)

"""
Testes unitarios para loader.py
Testa se loader.py delega corretamente para ChromaVectorStore (shared/vector_store.py)

Requer: chromadb instalado (pip install chromadb)
"""

import pytest
from unittest.mock import Mock, patch

try:
    from loader import get_chromadb_stats, load_documents_to_chromadb, query_chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb nao instalado")


class TestLoadDocumentsToChromadb:
    """Testes para load_documents_to_chromadb"""

    @patch("loader._vector_store")
    def test_load_delegates_to_vector_store(self, mock_store, sample_documents):
        """Delega para _vector_store.load_documents com os argumentos padrao"""
        load_documents_to_chromadb(sample_documents)

        mock_store.load_documents.assert_called_once_with(
            sample_documents, source="riotur", replace_existing=True
        )

    @patch("loader._vector_store")
    def test_load_delegates_custom_source_and_mode(self, mock_store, sample_documents):
        """Repassa source e replace_existing customizados"""
        load_documents_to_chromadb(sample_documents, source="google_places", replace_existing=False)

        mock_store.load_documents.assert_called_once_with(
            sample_documents, source="google_places", replace_existing=False
        )

    @patch("loader._vector_store")
    def test_load_returns_vector_store_result(self, mock_store, sample_documents):
        """Retorna o que _vector_store.load_documents devolver"""
        mock_collection = Mock()
        mock_store.load_documents.return_value = mock_collection

        result = load_documents_to_chromadb(sample_documents)

        assert result is mock_collection

    @patch("loader._vector_store")
    def test_load_with_empty_list(self, mock_store):
        """Lista vazia nao quebra"""
        load_documents_to_chromadb([])

        mock_store.load_documents.assert_called_once_with([], source="riotur", replace_existing=True)


class TestQueryChromadb:
    """Testes para query_chromadb"""

    @patch("loader._vector_store")
    def test_query_delegates_to_vector_store(self, mock_store):
        """Delega para _vector_store.search_documents"""
        mock_store.search_documents.return_value = [{"id": "id1"}]

        results = query_chromadb("Museu no Rio")

        mock_store.search_documents.assert_called_once_with("Museu no Rio", n_results=5)
        assert results == [{"id": "id1"}]


class TestGetChromadbStats:
    """Testes para get_chromadb_stats"""

    @patch("loader._vector_store")
    def test_stats_delegates_to_vector_store(self, mock_store):
        """Delega para _vector_store.get_stats"""
        mock_store.get_stats.return_value = {"total_documentos": 214, "status": "ativo"}

        stats = get_chromadb_stats()

        mock_store.get_stats.assert_called_once()
        assert stats == {"total_documentos": 214, "status": "ativo"}

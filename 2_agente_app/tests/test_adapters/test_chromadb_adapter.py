"""
Testes unitarios para adapters/chromadb_adapter.py

Requer: chromadb instalado (pip install chromadb)
"""

from unittest.mock import Mock

import pytest

try:
    from shared.vector_store import ChromaVectorStore
    from adapters.chromadb_adapter import ChromaDBAdapter
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb nao instalado")


@pytest.fixture
def raw_search_result():
    """Resultado bruto no formato devolvido por ChromaVectorStore.search_documents"""
    return {
        "id": "cultura-arte-museu-naval",
        "document": "Museu Naval e um ponto turistico no Rio de Janeiro.",
        "metadata": {
            "nome": "Museu Naval",
            "categoria": "cultura-arte",
            "endereco": "Rua Dom Manuel, 15 - Centro",
            "telefone": "+55 21 2104-6851",
            "horario": "quinta a domingo, das 13h as 17h",
            "website": "",
            "url_riotur": "https://visit.rio/o-que-fazer/museu-naval/",
            "fonte": "riotur",
        },
        "distance": 0.32,
    }


class TestChromaDBAdapter:
    """Testes para ChromaDBAdapter"""

    def test_search_delegates_to_vector_store(self, raw_search_result):
        """search() delega para vector_store.search_documents com os argumentos corretos"""
        mock_vector_store = Mock(spec=ChromaVectorStore)
        mock_vector_store.search_documents.return_value = [raw_search_result]

        adapter = ChromaDBAdapter(vector_store=mock_vector_store)
        adapter.search("museu no centro", n_results=3)

        mock_vector_store.search_documents.assert_called_once_with("museu no centro", n_results=3)

    def test_search_maps_metadata_to_tourist_spot(self, raw_search_result):
        """Cada campo de metadata e mapeado corretamente para TouristSpot"""
        mock_vector_store = Mock(spec=ChromaVectorStore)
        mock_vector_store.search_documents.return_value = [raw_search_result]

        adapter = ChromaDBAdapter(vector_store=mock_vector_store)
        results = adapter.search("museu no centro")
        spot = results[0].spot

        assert spot.name == "Museu Naval"
        assert spot.category == "cultura-arte"
        assert spot.address == "Rua Dom Manuel, 15 - Centro"
        assert spot.phone == "+55 21 2104-6851"
        assert spot.hours == "quinta a domingo, das 13h as 17h"
        assert spot.source_url == "https://visit.rio/o-que-fazer/museu-naval/"
        assert spot.source == "riotur"

    def test_search_maps_document_and_distance(self, raw_search_result):
        """document e distance sao repassados para SearchResult"""
        mock_vector_store = Mock(spec=ChromaVectorStore)
        mock_vector_store.search_documents.return_value = [raw_search_result]

        adapter = ChromaDBAdapter(vector_store=mock_vector_store)
        result = adapter.search("museu no centro")[0]

        assert result.document == "Museu Naval e um ponto turistico no Rio de Janeiro."
        assert result.distance == 0.32

    def test_search_with_missing_distance_defaults_to_zero(self, raw_search_result):
        """distance None (sem 'distances' no resultado) vira 0.0, nao None"""
        raw_search_result["distance"] = None
        mock_vector_store = Mock(spec=ChromaVectorStore)
        mock_vector_store.search_documents.return_value = [raw_search_result]

        adapter = ChromaDBAdapter(vector_store=mock_vector_store)
        result = adapter.search("museu no centro")[0]

        assert result.distance == 0.0

    def test_search_with_no_results_returns_empty_list(self):
        """Lista vazia de resultados brutos vira lista vazia de SearchResult"""
        mock_vector_store = Mock(spec=ChromaVectorStore)
        mock_vector_store.search_documents.return_value = []

        adapter = ChromaDBAdapter(vector_store=mock_vector_store)
        results = adapter.search("nada encontrado")

        assert results == []

    def test_default_constructor_creates_chroma_vector_store(self):
        """Sem vector_store explicito, cria uma ChromaVectorStore de verdade"""
        adapter = ChromaDBAdapter()

        assert isinstance(adapter._vector_store, ChromaVectorStore)

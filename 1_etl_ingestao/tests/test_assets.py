"""
Testes de integracao para assets Dagster
Testa se os assets produzem os artefatos esperados
"""

import sys
from pathlib import Path
import json
import pytest
from unittest.mock import Mock, patch

# Garante que o modulo run_etl esta no path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from loader import load_documents_to_chromadb, get_chromadb_stats
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class TestRioturDocumentsAsset:
    """Testes para o asset 3: riotur_documents"""

    def test_asset_transforms_items_to_documents(self, museu_naval_item):
        """Asset 3 recebe detalhes e produz documentos validos"""
        from document_transformer import transform_items_to_documents

        docs = transform_items_to_documents([museu_naval_item])
        assert len(docs) == 1
        assert docs[0]["id"] is not None
        assert len(docs[0]["document"]) > 0
        assert docs[0]["metadata"]["nome"] == "Museu Naval"

    def test_asset_preserves_all_metadata_fields(self, museu_naval_item):
        """Metadados preservam todos os campos relevantes"""
        from document_transformer import transform_items_to_documents

        docs = transform_items_to_documents([museu_naval_item])
        metadata = docs[0]["metadata"]

        required_fields = ["nome", "secao", "categoria", "endereco", "telefone"]
        for field in required_fields:
            assert field in metadata, "Campo '{}' ausente nos metadados".format(field)

    def test_asset_handles_multiple_sections(self, museu_naval_item, ago_item, copacabana_palace_item):
        """Asset processa itens de diferentes secoes"""
        from document_transformer import transform_items_to_documents

        items = [museu_naval_item, ago_item, copacabana_palace_item]
        docs = transform_items_to_documents(items)

        sections = {doc["metadata"]["secao"] for doc in docs}
        assert "o-que-fazer" in sections
        assert "onde-comer" in sections
        assert "onde-ficar" in sections


class TestChromadbAsset:
    """Testes para o asset 4: chromadb_turismo_rio"""

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb nao instalado")
    @patch("loader._vector_store")
    def test_asset_loads_documents(self, mock_store, sample_documents):
        """Asset 4 carrega documentos no ChromaDB"""
        load_documents_to_chromadb(sample_documents)

        assert mock_store.load_documents.called

    @pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb nao instalado")
    @patch("loader._vector_store")
    def test_asset_stats_reflect_loaded_docs(self, mock_store, sample_documents):
        """Apos carga, stats refletem o numero de documentos"""
        mock_store.get_stats.return_value = {
            "total_documentos": len(sample_documents),
            "status": "ativo",
        }

        load_documents_to_chromadb(sample_documents)
        stats = get_chromadb_stats()

        assert stats["total_documentos"] == len(sample_documents)
        assert stats["status"] == "ativo"


class TestDataRawJsonFiles:
    """Testes para validacao dos arquivos JSON em data_raw/"""

    @pytest.mark.integration
    def test_riotur_details_json_exists(self):
        """Arquivo riotur_details.json existe e tem dados validos"""
        filepath = Path("data_raw/riotur_details.json")
        if not filepath.exists():
            pytest.skip("Arquivo riotur_details.json nao encontrado")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "nome" in first
        assert "descricao" in first

    @pytest.mark.integration
    def test_riotur_links_json_exists(self):
        """Arquivo riotur_links.json existe e tem dados validos"""
        filepath = Path("data_raw/riotur_links.json")
        if not filepath.exists():
            pytest.skip("Arquivo riotur_links.json nao encontrado")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        # Sem contagem exata: o numero de itens muda a cada extracao do site
        assert len(data) > 0

        first = data[0]
        assert "nome" in first
        assert "url" in first
        assert "secao" in first

    @pytest.mark.integration
    def test_riotur_documents_json_exists(self):
        """Arquivo riotur_documents.json existe e tem dados validos"""
        filepath = Path("data_raw/riotur_documents.json")
        if not filepath.exists():
            pytest.skip("Arquivo riotur_documents.json nao encontrado")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) >= 200

        first = data[0]
        assert "id" in first
        assert "document" in first
        assert "metadata" in first
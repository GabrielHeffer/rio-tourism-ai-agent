"""
Testes unitarios para shared/vector_store.py
Testa a classe ChromaVectorStore com ChromaDB mockado

Requer: chromadb instalado (pip install chromadb)
"""

import tempfile
import threading
import time
from pathlib import Path

import pytest
from unittest.mock import Mock, patch

try:
    from shared.vector_store import ChromaVectorStore, PROJECT_ROOT, prefixos_do_modelo
    from shared.settings import EMBEDDING_MODEL
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb nao instalado")


@pytest.fixture
def sample_documents():
    """Lista de 2 documentos prontos para testar a vector store"""
    return [
        {
            "id": "cultura-arte-museu-naval",
            "document": "Museu Naval e um ponto turistico no Rio de Janeiro.",
            "metadata": {"nome": "Museu Naval", "categoria": "cultura-arte"}
        },
        {
            "id": "cultura-arte-ago",
            "document": "AGO e um espaco cultural no Rio de Janeiro.",
            "metadata": {"nome": "AGO", "categoria": "cultura-arte"}
        },
    ]


class TestGetCollection:
    """Testes para _get_collection (conexao + embedding function)"""

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_get_collection_passes_embedding_function(self, mock_client):
        """get_or_create_collection recebe uma embedding_function nao-nula (regressao do bug multilingue)"""
        mock_client.return_value.get_or_create_collection.return_value = Mock()

        store = ChromaVectorStore(db_path=Path("."))
        store._get_collection(create=True)

        call_kwargs = mock_client.return_value.get_or_create_collection.call_args[1]
        assert call_kwargs["embedding_function"] is not None

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_get_collection_uses_multilingual_model(self, mock_client):
        """A embedding function usa o modelo multilingue configurado na classe"""
        mock_client.return_value.get_or_create_collection.return_value = Mock()

        store = ChromaVectorStore(db_path=Path("."))
        embedding_function = store._get_embedding_function()

        assert EMBEDDING_MODEL == "intfloat/multilingual-e5-small"
        assert embedding_function is not None

    def test_modelo_de_embedding_vem_do_ambiente(self, monkeypatch):
        """EMBEDDING_MODEL pode ser trocado por variavel de ambiente"""
        import importlib
        import shared.settings

        monkeypatch.setenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
        recarregado = importlib.reload(shared.settings)
        try:
            assert recarregado.EMBEDDING_MODEL == "intfloat/multilingual-e5-base"
        finally:
            monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
            importlib.reload(shared.settings)

    def test_prefixos_acompanham_a_familia_do_modelo(self):
        """Modelo E5 usa prefixos; outra familia nao leva prefixo nenhum"""
        assert prefixos_do_modelo("intfloat/multilingual-e5-small") == ("passage: ", "query: ")
        assert prefixos_do_modelo("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") == ("", "")

    def test_indexacao_usa_prefixo_de_passagem(self):
        """Documentos indexados levam "passage: ", exigido pelos modelos E5"""
        store = ChromaVectorStore(db_path=Path("."))
        funcao = store._get_embedding_function()
        funcao._delegate = Mock(return_value=[[0.0]])

        funcao(["Museu Naval"])

        assert funcao._delegate.call_args[0][0] == ["passage: Museu Naval"]

    def test_busca_usa_prefixo_de_query(self, monkeypatch):
        """Perguntas levam "query: ", o par assimetrico do prefixo de passagem"""
        capturado = {}

        class FakeDelegate:
            def __call__(self, textos):
                capturado["textos"] = textos
                return [[0.0]]

        store = ChromaVectorStore(db_path=Path("."))
        monkeypatch.setattr(
            "shared.vector_store.embedding_functions.SentenceTransformerEmbeddingFunction",
            lambda **kwargs: FakeDelegate(),
        )

        store._embed_query("onde comer sushi")

        assert capturado["textos"] == ["query: onde comer sushi"]

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_get_collection_read_only_does_not_create(self, mock_client):
        """create=False usa get_collection, nao get_or_create_collection"""
        mock_client.return_value.get_collection.return_value = Mock()

        store = ChromaVectorStore(db_path=Path("."))
        store._get_collection(create=False)

        mock_client.return_value.get_collection.assert_called_once()
        mock_client.return_value.get_or_create_collection.assert_not_called()

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_db_path_respects_env_var(self, mock_client, monkeypatch):
        """db_path usa CHROMA_DB_PATH quando definido, sem precisar de override manual"""
        monkeypatch.setenv("CHROMA_DB_PATH", "custom_chroma_path")

        store = ChromaVectorStore()

        assert store._db_path.name == "custom_chroma_path"

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_db_path_relativo_ancora_na_raiz_do_projeto(self, mock_client, monkeypatch):
        """Caminho relativo e resolvido contra a raiz, nao contra o cwd.

        Regressao: o ETL roda de 1_etl_ingestao/ e o agente da raiz. Resolvendo
        contra o cwd, cada um criava seu proprio banco e o agente nao achava a
        collection gravada pelo ETL.
        """
        monkeypatch.setenv("CHROMA_DB_PATH", "chroma_db_rio")

        store = ChromaVectorStore()

        assert store._db_path.is_absolute()
        assert store._db_path == PROJECT_ROOT / "chroma_db_rio"

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_db_path_absoluto_e_respeitado(self, mock_client, monkeypatch):
        """CHROMA_DB_PATH absoluto nao e reescrito para dentro do projeto"""
        absoluto = Path(tempfile.gettempdir()).resolve() / "chroma_fora_do_projeto"
        monkeypatch.setenv("CHROMA_DB_PATH", str(absoluto))

        store = ChromaVectorStore()

        assert store._db_path == absoluto


class TestConcurrentAccess:
    """Buscas em paralelo (tool calls simultaneas do agente) nao podem duplicar a inicializacao"""

    THREAD_COUNT = 5

    def _run_in_parallel(self, target) -> None:
        """Dispara target em varias threads liberadas ao mesmo tempo por uma barreira"""
        barrier = threading.Barrier(self.THREAD_COUNT)

        def worker():
            barrier.wait()
            target()

        threads = [threading.Thread(target=worker) for _ in range(self.THREAD_COUNT)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_parallel_get_client_creates_single_client(self, mock_client, tmp_path):
        """Varias threads pedindo o client ao mesmo tempo criam um unico PersistentClient"""
        # Criacao lenta amplia a janela da condicao de corrida que existia antes da trava
        mock_client.side_effect = lambda **kwargs: time.sleep(0.05) or Mock()

        store = ChromaVectorStore(db_path=tmp_path)
        self._run_in_parallel(store._get_client)

        assert mock_client.call_count == 1

    def test_query_embedding_function_is_created_once(self, monkeypatch):
        """O modelo de embeddings das perguntas e carregado uma vez, nao a cada busca"""
        creations = []

        def fake_embedding_function(**kwargs):
            creations.append(kwargs)
            time.sleep(0.05)
            return lambda textos: [[0.0] for _ in textos]

        monkeypatch.setattr(
            "shared.vector_store.embedding_functions.SentenceTransformerEmbeddingFunction",
            fake_embedding_function,
        )

        store = ChromaVectorStore(db_path=Path("."))
        self._run_in_parallel(lambda: store._embed_query("sushi"))
        store._embed_query("museus")

        assert len(creations) == 1


class TestLoadDocuments:
    """Testes para load_documents"""

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_load_replace_existing_deletes_before_insert(self, mock_client, sample_documents):
        """replace_existing=True (padrao) remove documentos antigos da fonte antes de inserir"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        store.load_documents(sample_documents, source="riotur")

        mock_collection.delete.assert_called_once_with(where={"fonte": "riotur"})
        assert mock_collection.add.called

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_load_append_does_not_delete(self, mock_client, sample_documents):
        """replace_existing=False so adiciona os novos, sem apagar nada"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        store.load_documents(sample_documents, source="riotur", replace_existing=False)

        mock_collection.delete.assert_not_called()
        assert mock_collection.add.called

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_load_tags_documents_with_source(self, mock_client, sample_documents):
        """Cada documento carregado recebe o campo 'fonte' no metadata"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        store.load_documents(sample_documents, source="google_places")

        metadatas = mock_collection.add.call_args[1]["metadatas"]
        assert all(metadata["fonte"] == "google_places" for metadata in metadatas)

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_load_with_empty_list(self, mock_client):
        """Lista vazia nao quebra"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        collection = store.load_documents([], source="riotur")

        assert collection is mock_collection


class TestSearchDocuments:
    """Testes para search_documents"""

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_search_returns_formatted_list(self, mock_client):
        """Busca retorna lista de resultados com id, document, metadata, distance"""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc"]],
            "metadatas": [[{"nome": "Teste"}]],
            "distances": [[0.5]],
        }
        mock_client.return_value.get_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        results = store.search_documents("Museu no Rio")

        assert len(results) == 1
        result = results[0]
        assert result["id"] == "id1"
        assert result["document"] == "doc"
        assert result["metadata"] == {"nome": "Teste"}
        assert result["distance"] == 0.5


class TestGetStats:
    """Testes para get_stats"""

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_stats_active_when_has_documents(self, mock_client):
        """Status 'ativo' quando ha documentos"""
        mock_collection = Mock()
        mock_collection.count.return_value = 214
        mock_client.return_value.get_collection.return_value = mock_collection

        store = ChromaVectorStore(db_path=Path("."))
        stats = store.get_stats()

        assert stats["total_documentos"] == 214
        assert stats["status"] == "ativo"

    @patch("shared.vector_store.chromadb.PersistentClient")
    def test_stats_error_returns_error_dict(self, mock_client):
        """Erro retorna dicionario com status 'erro'"""
        mock_client.side_effect = Exception("Falha de conexao")

        store = ChromaVectorStore(db_path=Path("."))
        stats = store.get_stats()

        assert stats["status"] == "erro"
        assert "mensagem" in stats

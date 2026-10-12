"""
Acesso compartilhado a base vetorial ChromaDB
Usado pelo pipeline ETL (1_etl_ingestao) e pelo agente (2_agente_app), garantindo
que documentos e queries sejam sempre embutidos pelo mesmo modelo multilingue.
"""

import os
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import EmbeddingFunction

from shared.settings import COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Raiz do projeto: shared/ fica um nivel abaixo dela.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_db_path() -> Path:
    """Resolve o caminho do banco vetorial de forma independente do cwd.

    O banco e compartilhado: o ETL roda de dentro de 1_etl_ingestao/ (obrigatorio,
    por causa dos imports do run_etl.py) e o agente roda da raiz. Se o caminho
    relativo fosse resolvido contra o cwd, cada um criaria seu proprio
    chroma_db_rio/ e o agente nunca acharia o que o ETL gravou.

    Um CHROMA_DB_PATH absoluto e respeitado como esta; um relativo e ancorado
    na raiz do projeto.
    """
    caminho = Path(os.getenv("CHROMA_DB_PATH") or "chroma_db_rio")
    return caminho if caminho.is_absolute() else PROJECT_ROOT / caminho


class PrefixedEmbeddingFunction(EmbeddingFunction):
    """Embedding function que aplica o prefixo exigido pelos modelos E5.

    Os modelos da familia E5 sao treinados com prefixos assimetricos: o texto
    indexado leva "passage: " e a pergunta leva "query: ". Sem eles a qualidade da
    recuperacao cai de forma significativa, porque o modelo deixa de distinguir os
    dois papeis.

    O prefixo e aplicado aqui, e nao no texto guardado, para o documento devolvido
    ao agente continuar limpo.
    """

    def __init__(self, model_name: str, prefix: str):
        self._delegate = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self._prefix = prefix

    def __call__(self, input):
        return self._delegate([self._prefix + str(texto) for texto in input])

    @staticmethod
    def name() -> str:
        """Identificador usado pelo ChromaDB ao serializar a configuracao"""
        return "prefixed_sentence_transformer"


def prefixos_do_modelo(model_name: str):
    """Descobre os prefixos de indexacao e de busca exigidos pelo modelo.

    Os modelos da familia E5 sao treinados com prefixos assimetricos
    ("passage: " no texto indexado, "query: " na pergunta) e perdem qualidade sem
    eles. Outras familias nao usam prefixo, e aplicar um atrapalharia - por isso a
    escolha acompanha o modelo em vez de ser fixa.

    Args:
        model_name: Identificador do modelo de embedding

    Returns:
        Tupla (prefixo_de_passagem, prefixo_de_query), possivelmente vazios.
    """
    if "e5" in model_name.lower():
        return "passage: ", "query: "
    return "", ""


class ChromaVectorStore:
    """Controla o acesso e a inserção de documentos na base vetorial compartilhada"""
    BATCH_SIZE = 50

    def __init__(
        self,
        db_path: Optional[Path] = None,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
    ):
        self._db_path = db_path or resolve_db_path()
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._passage_prefix, self._query_prefix = prefixos_do_modelo(embedding_model)
        self._client: Optional[chromadb.ClientAPI] = None
        self._passage_embedding_function: Optional[EmbeddingFunction] = None
        self._query_embedding_function: Optional[EmbeddingFunction] = None
        # O agente pode executar varias buscas em paralelo (o ToolNode do LangGraph
        # roda as tool calls de uma mesma resposta em threads). Sem esta trava, duas
        # threads criavam o PersistentClient ao mesmo tempo e o ChromaDB quebrava com
        # "Could not connect to tenant default_tenant".
        self._init_lock = threading.Lock()

    def _get_client(self) -> chromadb.ClientAPI:
        """Cria (ou reaproveita) o client persistente do ChromaDB, uma unica vez por instancia"""
        if self._client is None:
            with self._init_lock:
                if self._client is None:
                    self._db_path.mkdir(parents=True, exist_ok=True)
                    self._client = chromadb.PersistentClient(path=str(self._db_path))
        return self._client

    def _get_embedding_function(self) -> EmbeddingFunction:
        """Embedding function usada ao indexar documentos (prefixo "passage: ").

        Criada uma vez e reaproveitada: cada instancia carrega o modelo de embeddings,
        e recriar a cada chamada custava segundos e dezenas de requisicoes ao HF Hub.
        """
        if self._passage_embedding_function is None:
            with self._init_lock:
                if self._passage_embedding_function is None:
                    self._passage_embedding_function = PrefixedEmbeddingFunction(
                        self._embedding_model, self._passage_prefix
                    )
        return self._passage_embedding_function

    def _get_query_embedding_function(self) -> EmbeddingFunction:
        """Embedding function usada nas perguntas (prefixo "query: "), criada uma vez"""
        if self._query_embedding_function is None:
            with self._init_lock:
                if self._query_embedding_function is None:
                    self._query_embedding_function = PrefixedEmbeddingFunction(
                        self._embedding_model, self._query_prefix
                    )
        return self._query_embedding_function

    def _embed_query(self, query_text: str) -> List[float]:
        """Embute a pergunta com o prefixo "query: " exigido pelos modelos E5.

        A collection guarda uma unica embedding function, que usa o prefixo de
        passagem. Por isso a pergunta e embutida aqui e enviada pronta ao ChromaDB
        via query_embeddings, em vez de passar por query_texts.
        """
        return self._get_query_embedding_function()([query_text])[0]

    def _get_collection(self, create: bool = True) -> Collection:
        """Retorna a collection compartilhada, com a embedding function multilingue configurada"""
        client = self._get_client()
        embedding_function = self._get_embedding_function()

        if create:
            self._descartar_collection_de_outro_modelo(client)
            return client.get_or_create_collection(
                name=self._collection_name,
                embedding_function=embedding_function,
                metadata={
                    "description": "Rio de Janeiro Tourism Database",
                    "embedding_model": self._embedding_model,
                }
            )

        return client.get_collection(
            name=self._collection_name,
            embedding_function=embedding_function
        )

    def _descartar_collection_de_outro_modelo(self, client: chromadb.ClientAPI) -> None:
        """Recria a collection quando ela foi gerada por outro modelo de embedding.

        Vetores de modelos diferentes nao sao comparaveis, mas o ChromaDB so recusa
        a insercao quando a dimensao muda. Modelos de mesma dimensao (o MiniLM
        anterior e o e5-small tem 384) passariam sem erro e a busca degradaria em
        silencio, que e bem pior do que falhar. A checagem fecha essa porta.
        """
        try:
            existente = client.get_collection(name=self._collection_name)
        except Exception:
            return  # ainda nao existe: nada a descartar

        modelo_atual = (existente.metadata or {}).get("embedding_model")
        if modelo_atual == self._embedding_model:
            return

        logger.warning(
            "Collection '%s' foi criada com o modelo %r e sera recriada para %r; "
            "os documentos precisam ser recarregados.",
            self._collection_name, modelo_atual, self._embedding_model,
        )
        client.delete_collection(name=self._collection_name)

    def load_documents(
        self, documents: List[Dict], source: str, replace_existing: bool = True
    ) -> Collection:
        """
        Insere documentos na base vetorial

        Args:
            documents: Lista de dicts com id, document, metadata
            source: Identificador da fonte dos dados (ex: "riotur", "google_places")
            replace_existing: Se True (padrão), remove antes os documentos antigos
                dessa fonte (fresh reload). Se False, só adiciona os novos (append),
                preservando os documentos já existentes dessa fonte.

        Returns:
            Collection do ChromaDB
        """
        collection = self._get_collection(create=True)

        if replace_existing:
            try:
                collection.delete(where={"fonte": source})
                logger.info("Documentos antigos da fonte '{}' removidos".format(source))
            except Exception as e:
                logger.warning("Nao foi possivel remover documentos antigos da fonte '{}': {}".format(source, e))

        logger.info("Carregando {} documentos em ChromaDB...".format(len(documents)))

        total = len(documents)
        carregados = 0
        batches_com_falha = 0
        primeiro_erro: Optional[Exception] = None

        for batch_start in range(0, total, self.BATCH_SIZE):
            batch_end = min(batch_start + self.BATCH_SIZE, total)
            batch = documents[batch_start:batch_end]

            ids = [doc["id"] for doc in batch]
            documents_text = [doc["document"] for doc in batch]
            metadatas = [{**doc["metadata"], "fonte": source} for doc in batch]

            try:
                collection.add(
                    ids=ids,
                    documents=documents_text,
                    metadatas=metadatas
                )
                carregados += len(batch)
                logger.info("[{}/{}] Batch carregado ({} documentos)".format(
                    batch_end, total, len(batch)))
            except Exception as e:
                batches_com_falha += 1
                if primeiro_erro is None:
                    primeiro_erro = e
                logger.exception("Erro ao carregar batch [{}-{}]: {}".format(
                    batch_start, batch_end, e))
                continue

        count = collection.count()

        # Nenhum documento entrou apesar de haver documentos para carregar: isso nao pode
        # passar como sucesso, senao o chamador reporta "[OK]" sobre uma base vazia.
        if total > 0 and carregados == 0:
            raise RuntimeError(
                "Nenhum dos {} documentos foi carregado em ChromaDB "
                "({} batches falharam). Primeiro erro: {}".format(
                    total, batches_com_falha, primeiro_erro)
            ) from primeiro_erro

        if batches_com_falha:
            logger.error(
                "[PARCIAL] {} de {} documentos carregados; {} batches falharam. "
                "Primeiro erro: {}".format(
                    carregados, total, batches_com_falha, primeiro_erro)
            )
        else:
            logger.info("[OK] {} documentos carregados em ChromaDB".format(carregados))

        logger.info("Total de documentos no ChromaDB: {}".format(count))

        return collection

    def search_documents(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """
        Faz busca semântica na base vetorial

        Args:
            query_text: Texto para buscar
            n_results: Número de resultados

        Returns:
            Lista de documentos encontrados com scores
        """
        collection = self._get_collection(create=False)

        logger.info("Buscando por: '{}'".format(query_text))

        results = collection.query(
            query_embeddings=[self._embed_query(query_text)],
            n_results=n_results
        )

        formatted_results = []

        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None
                })

        return formatted_results

    def get_stats(self) -> Dict:
        """Retorna estatísticas da base vetorial"""
        try:
            collection = self._get_collection(create=False)
            count = collection.count()

            return {
                "total_documentos": count,
                "status": "ativo" if count > 0 else "vazio"
            }
        except Exception as e:
            logger.exception("Erro ao obter stats: {}".format(e))
            return {"status": "erro", "mensagem": str(e)}

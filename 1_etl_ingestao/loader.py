"""
Carregador de Dados para ChromaDB
Facade fina sobre ChromaVectorStore (shared/vector_store.py)
"""

import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.vector_store import ChromaVectorStore
from shared.settings import COLLECTION_NAME

_vector_store = ChromaVectorStore(collection_name=COLLECTION_NAME)


def load_documents_to_chromadb(
    documents: List[Dict], source: str = "riotur", replace_existing: bool = True
):
    """
    Carrega documentos em ChromaDB com embeddings

    Args:
        documents: Lista de dicts com id, document, metadata
        source: Identificador da fonte dos dados (ex: "riotur", "google_places")
        replace_existing: Se True (padrão), substitui os documentos antigos
            dessa fonte. Se False, só adiciona os novos (append).

    Returns:
        Collection do ChromaDB
    """
    return _vector_store.load_documents(documents, source=source, replace_existing=replace_existing)


def query_chromadb(query_text: str, n_results: int = 5) -> List[Dict]:
    """
    Faz busca semântica no ChromaDB

    Args:
        query_text: Texto para buscar
        n_results: Número de resultados

    Returns:
        Lista de documentos encontrados com scores
    """
    return _vector_store.search_documents(query_text, n_results=n_results)


def get_chromadb_stats() -> Dict:
    """Retorna estatísticas do ChromaDB"""
    return _vector_store.get_stats()

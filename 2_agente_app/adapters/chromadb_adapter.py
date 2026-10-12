"""
Adapter que implementa VectorStorePort usando ChromaVectorStore (shared/vector_store.py)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.vector_store import ChromaVectorStore

from domain.search_result import SearchResult
from domain.tourist_spot import TouristSpot
from ports.vector_store_port import VectorStorePort

from shared.settings import COLLECTION_NAME


class ChromaDBAdapter(VectorStorePort):
    """Implementa VectorStorePort sobre a base vetorial compartilhada ChromaDB"""

    def __init__(self, vector_store: Optional[ChromaVectorStore] = None):
        self._vector_store = vector_store or ChromaVectorStore(collection_name=COLLECTION_NAME)

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Busca na base vetorial e mapeia cada resultado bruto para o dominio"""
        raw_results = self._vector_store.search_documents(query, n_results=n_results)
        return [self._to_search_result(raw_result) for raw_result in raw_results]

    def _to_search_result(self, raw_result: Dict) -> SearchResult:
        """Converte um dict bruto do ChromaDB em SearchResult/TouristSpot"""
        metadata = raw_result.get("metadata", {})
        spot = TouristSpot(
            name=metadata.get("nome", ""),
            category=metadata.get("categoria", ""),
            address=metadata.get("endereco", ""),
            phone=metadata.get("telefone", ""),
            hours=metadata.get("horario", ""),
            website=metadata.get("website", ""),
            source_url=metadata.get("url_riotur", ""),
            source=metadata.get("fonte", ""),
        )
        return SearchResult(
            spot=spot,
            document=raw_result.get("document", ""),
            distance=raw_result.get("distance") or 0.0,
        )

"""
Porta (contrato) para busca semantica na base vetorial de turismo
"""

from abc import ABC, abstractmethod
from typing import List

from domain.search_result import SearchResult


class VectorStorePort(ABC):
    """Contrato de leitura para busca semantica de pontos turisticos"""

    @abstractmethod
    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Busca pontos turisticos por similaridade semantica com o texto da query"""
        raise NotImplementedError

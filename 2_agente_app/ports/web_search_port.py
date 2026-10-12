"""
Porta (contrato) para busca na web
"""

from abc import ABC, abstractmethod
from typing import List

from domain.web_result import WebResult


class WebSearchPort(ABC):
    """Contrato de busca na web, independente do provedor (Tavily, Brave, ...)"""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        """Busca paginas na web relacionadas a query"""
        raise NotImplementedError

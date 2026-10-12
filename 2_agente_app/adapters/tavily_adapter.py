"""
Adapter que implementa WebSearchPort usando a API de busca do Tavily
"""

import logging
import os
from typing import Dict, List, Optional

from tavily import TavilyClient

from domain.web_result import WebResult
from ports.web_search_port import WebSearchPort

logger = logging.getLogger(__name__)

# Busca "basic" gasta menos creditos do plano gratuito e ja traz trechos suficientes
SEARCH_DEPTH = "basic"


class TavilyAdapter(WebSearchPort):
    """Implementa WebSearchPort usando o Tavily (API de busca feita para agentes de IA)"""

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY nao configurada")
        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        """Busca na web; em caso de falha da API devolve lista vazia, sem derrubar a conversa"""
        # O SDK do Tavily nao gera log proprio: sem esta linha as buscas (e os creditos
        # gastos) ficavam invisiveis no terminal
        logger.info("Buscando na web por: '{}'".format(query))
        try:
            response = self._client.search(
                query=query, max_results=max_results, search_depth=SEARCH_DEPTH
            )
        except Exception as e:
            logger.warning("Falha na busca na web por '{}': {}".format(query, e))
            return []

        return [_build_web_result(raw_result) for raw_result in response.get("results", [])]


def _build_web_result(raw_result: Dict) -> WebResult:
    """Converte um resultado bruto do Tavily em WebResult (campo ausente vira string vazia)"""
    return WebResult(
        title=raw_result.get("title") or "",
        url=raw_result.get("url") or "",
        content=raw_result.get("content") or "",
        published_date=raw_result.get("published_date") or "",
    )

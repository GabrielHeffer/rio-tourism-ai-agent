"""
Entidade de dominio: resultado de uma busca na web
"""

from dataclasses import dataclass


@dataclass
class WebResult:
    """Uma pagina encontrada na busca na web, com o trecho relevante do conteudo.

    Todos os campos sao strings, nunca None: campo ausente na resposta do provedor
    vira string vazia.
    """

    title: str
    url: str
    content: str
    published_date: str

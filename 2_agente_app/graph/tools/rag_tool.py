"""
Ferramenta de RAG do agente: busca semantica na base turistica do Rio de Janeiro
"""

from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from domain.search_result import SearchResult
from ports.vector_store_port import VectorStorePort

DEFAULT_N_RESULTS = 5


class SearchTouristSpotsInput(BaseModel):
    """Schema de entrada da ferramenta de busca turistica"""

    query: str = Field(
        description=(
            "Termo de busca sobre o que procurar na cidade. "
            "A base cobre APENAS o Rio de Janeiro, entao NAO inclua 'Rio de Janeiro' "
            "nem 'no Rio' na busca: essa expressao aparece em quase todos os "
            "documentos e faz a busca perder precisao. "
            "Prefira termos curtos e especificos. "
            "Bom: 'sushi', 'culinaria japonesa', 'museus em Copacabana', "
            "'bares com musica ao vivo'. "
            "Ruim: 'comida asiatica no Rio de Janeiro', "
            "'quais restaurantes posso visitar na cidade do Rio'."
        )
    )


def build_search_tourist_spots_tool(vector_store: VectorStorePort) -> StructuredTool:
    """Cria a ferramenta de busca turistica injetando a porta de vector store"""

    def _search_tourist_spots(query: str) -> str:
        results = vector_store.search(query, n_results=DEFAULT_N_RESULTS)
        return _format_search_results(results)

    return StructuredTool.from_function(
        func=_search_tourist_spots,
        name="search_tourist_spots",
        description=(
            "Busca pontos turisticos, restaurantes e hospedagens no Rio de Janeiro "
            "por similaridade semantica. Use para responder perguntas sobre o que "
            "fazer, onde comer ou onde se hospedar na cidade."
        ),
        args_schema=SearchTouristSpotsInput,
    )


def _format_search_results(results: List[SearchResult]) -> str:
    """Formata os resultados da busca em texto legivel para o LLM usar como contexto"""
    if not results:
        return "Nenhum resultado encontrado para essa busca."

    formatted_spots = [
        _format_single_result(position, result)
        for position, result in enumerate(results, start=1)
    ]
    return "\n\n".join(formatted_spots)


def _format_single_result(position: int, result: SearchResult) -> str:
    """Formata um unico resultado de busca como um bloco de texto numerado"""
    spot = result.spot
    lines = ["{}. {} ({})".format(position, spot.name, spot.category)]

    if spot.address:
        lines.append("Endereco: {}".format(spot.address))
    if spot.hours:
        lines.append("Horario: {}".format(spot.hours))
    if spot.phone:
        lines.append("Telefone: {}".format(spot.phone))
    if spot.website:
        lines.append("Site: {}".format(spot.website))

    lines.append(result.document)
    return "\n".join(lines)

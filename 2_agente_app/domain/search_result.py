"""
Entidade de dominio: resultado de uma busca semantica na base vetorial
"""

from dataclasses import dataclass

from .tourist_spot import TouristSpot


@dataclass
class SearchResult:
    """Um resultado de busca semantica, com o ponto turistico e o texto usado na busca"""

    spot: TouristSpot
    document: str
    distance: float

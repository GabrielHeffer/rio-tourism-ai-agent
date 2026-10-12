"""
Entidade de dominio: ponto turistico, restaurante ou hospedagem no Rio de Janeiro
"""

from dataclasses import dataclass


@dataclass
class TouristSpot:
    """Representa um item turistico (o que fazer, onde comer ou onde ficar)"""

    name: str
    category: str
    address: str
    phone: str
    hours: str
    website: str
    source_url: str
    source: str

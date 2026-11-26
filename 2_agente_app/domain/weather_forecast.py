"""
Entidade de dominio: previsao do tempo de um dia na cidade do Rio de Janeiro
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class DailyForecast:
    """Previsao diaria: condicao do ceu, temperaturas, chuva, vento e indice UV"""

    day: date
    description: str
    temperature_min: float
    temperature_max: float
    precipitation_probability: int
    precipitation_mm: float
    wind_max_kmh: float
    uv_index_max: float

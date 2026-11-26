"""
Porta (contrato) para previsao do tempo
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from domain.weather_forecast import DailyForecast


class WeatherPort(ABC):
    """Contrato de previsao do tempo diaria, independente do provedor (Open-Meteo, OpenWeather, ...)"""

    @abstractmethod
    def fetch_daily_forecast(self, start_day: date, end_day: date) -> List[DailyForecast]:
        """Busca a previsao de cada dia entre start_day e end_day (inclusive)"""
        raise NotImplementedError

"""
Testes unitarios para ports/weather_port.py
"""

from datetime import date
from typing import List

import pytest

from domain.weather_forecast import DailyForecast
from ports.weather_port import WeatherPort


class TestWeatherPort:
    """Testes para o contrato WeatherPort"""

    def test_cannot_instantiate_directly(self):
        """WeatherPort e abstrata e nao pode ser instanciada diretamente"""
        with pytest.raises(TypeError):
            WeatherPort()

    def test_subclass_without_fetch_cannot_be_instantiated(self):
        """Subclasse que nao implementa fetch_daily_forecast tambem nao pode ser instanciada"""

        class IncompleteAdapter(WeatherPort):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_implementing_fetch_can_be_instantiated(self):
        """Subclasse que implementa fetch_daily_forecast instancia normalmente"""

        class FakeAdapter(WeatherPort):
            def fetch_daily_forecast(self, start_day: date, end_day: date) -> List[DailyForecast]:
                return []

        assert isinstance(FakeAdapter(), WeatherPort)

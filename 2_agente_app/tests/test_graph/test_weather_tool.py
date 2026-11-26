"""
Testes unitarios para graph/tools/weather_tool.py (tool de previsao do tempo)
"""

from datetime import date
from typing import List

from langchain_core.tools import StructuredTool

from domain.weather_forecast import DailyForecast
from graph.tools.weather_tool import WEATHER_SOURCE_LINE, build_weather_forecast_tool
from ports.weather_port import WeatherPort

TODAY = date(2026, 11, 17)


class FakeWeatherPort(WeatherPort):
    """Fake de teste para WeatherPort, registra o periodo pedido"""

    def __init__(self, forecasts: List[DailyForecast]):
        self._forecasts = forecasts
        self.requested_period = None

    def fetch_daily_forecast(self, start_day: date, end_day: date) -> List[DailyForecast]:
        self.requested_period = (start_day, end_day)
        return self._forecasts


def build_saturday_forecast() -> DailyForecast:
    return DailyForecast(
        day=date(2026, 11, 21),
        description="nublado",
        temperature_min=24.3,
        temperature_max=31.3,
        precipitation_probability=31,
        precipitation_mm=0.0,
        wind_max_kmh=11.0,
        uv_index_max=8.4,
    )


def build_tool(fake_port: FakeWeatherPort) -> StructuredTool:
    return build_weather_forecast_tool(fake_port, current_date_provider=lambda: TODAY)


class TestBuildWeatherForecastTool:
    """Testes para build_weather_forecast_tool"""

    def test_tool_is_named_fetch_weather_forecast(self):
        """A tool tem o nome que o LLM usa para chama-la"""
        assert build_tool(FakeWeatherPort([])).name == "fetch_weather_forecast"

    def test_formats_one_line_per_day_with_full_date(self):
        """Cada dia sai com a data por extenso, a condicao, temperaturas e chance de chuva"""
        tool = build_tool(FakeWeatherPort([build_saturday_forecast()]))

        output = tool.invoke({"start_date": "2026-11-21"})

        assert "sábado, 21 de novembro de 2026: nublado, 24–31 °C, chance de chuva 31%" in output

    def test_output_ends_with_open_meteo_source(self):
        """A previsao cita a fonte (exigencia da licenca CC BY 4.0)"""
        tool = build_tool(FakeWeatherPort([build_saturday_forecast()]))

        output = tool.invoke({"start_date": "2026-11-21"})

        assert output.endswith(WEATHER_SOURCE_LINE)

    def test_missing_end_date_uses_start_date(self):
        """Sem data final, a consulta e de um dia so"""
        fake_port = FakeWeatherPort([build_saturday_forecast()])

        build_tool(fake_port).invoke({"start_date": "2026-11-21"})

        assert fake_port.requested_period == (date(2026, 11, 21), date(2026, 11, 21))

    def test_empty_forecast_returns_friendly_message(self):
        """Falha do provedor vira mensagem clara, sem texto vazio"""
        output = build_tool(FakeWeatherPort([])).invoke({"start_date": "2026-11-21"})

        assert output == "Não foi possível consultar a previsão do tempo agora."


class TestForecastRangeValidation:
    """Datas fora do alcance da previsao nao chegam ao provedor"""

    def test_past_date_is_rejected_without_calling_port(self):
        """Data passada devolve mensagem e nao consulta a API"""
        fake_port = FakeWeatherPort([build_saturday_forecast()])

        output = build_tool(fake_port).invoke({"start_date": "2026-11-10"})

        assert "Só há previsão de hoje" in output
        assert fake_port.requested_period is None

    def test_date_beyond_forecast_range_is_rejected(self):
        """Data alem de 16 dias informa ate quando vai a previsao e nao consulta a API"""
        fake_port = FakeWeatherPort([build_saturday_forecast()])

        output = build_tool(fake_port).invoke({"start_date": "2026-12-25"})

        assert "Ainda não há previsão" in output
        assert "2 de dezembro de 2026" in output
        assert fake_port.requested_period is None

    def test_invalid_date_returns_clear_message(self):
        """Data em formato errado devolve instrucao do formato esperado"""
        fake_port = FakeWeatherPort([])

        output = build_tool(fake_port).invoke({"start_date": "21/11/2026"})

        assert output == "Data inválida: use o formato AAAA-MM-DD."
        assert fake_port.requested_period is None

    def test_end_before_start_is_rejected(self):
        """Periodo invertido devolve mensagem clara"""
        output = build_tool(FakeWeatherPort([])).invoke(
            {"start_date": "2026-11-22", "end_date": "2026-11-21"}
        )

        assert output == "Período inválido: a data final é anterior à inicial."

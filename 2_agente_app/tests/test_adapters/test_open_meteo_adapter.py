"""
Testes unitarios para adapters/open_meteo_adapter.py (nenhum teste chama a API real)
"""

from datetime import date
from unittest.mock import Mock, patch

from adapters.open_meteo_adapter import (
    RIO_LATITUDE,
    RIO_LONGITUDE,
    TIMEZONE,
    UNKNOWN_WEATHER_DESCRIPTION,
    OpenMeteoAdapter,
    describe_weather_code,
)


def build_open_meteo_payload() -> dict:
    """Resposta real do Open-Meteo para 21 e 22/11/2026 (consultada em 17/11/2026)"""
    return {
        "latitude": -22.952549,
        "longitude": -43.215027,
        "timezone": "America/Sao_Paulo",
        "daily": {
            "time": ["2026-11-21", "2026-11-22"],
            "weather_code": [3, 3],
            "temperature_2m_max": [31.3, 33.3],
            "temperature_2m_min": [24.3, 25.0],
            "precipitation_probability_max": [31, 34],
            "precipitation_sum": [0.00, 0.00],
            "wind_speed_10m_max": [11.0, 16.0],
            "uv_index_max": [8.40, 8.10],
        },
    }


def build_response(payload: dict) -> Mock:
    response = Mock()
    response.json.return_value = payload
    return response


class TestDescribeWeatherCode:
    """Traducao dos codigos WMO para portugues"""

    def test_known_code_becomes_portuguese_description(self):
        """Codigo 3 e 'nublado' e 63 e 'chuva moderada'"""
        assert describe_weather_code(3) == "nublado"
        assert describe_weather_code(63) == "chuva moderada"

    def test_unknown_code_becomes_default_text(self):
        """Codigo fora da tabela (ou ausente) vira o texto padrao"""
        assert describe_weather_code(1234) == UNKNOWN_WEATHER_DESCRIPTION
        assert describe_weather_code(None) == UNKNOWN_WEATHER_DESCRIPTION


class TestFetchDailyForecast:
    """Testes para a consulta e a conversao da resposta"""

    @patch("adapters.open_meteo_adapter.requests.get")
    def test_converts_response_to_daily_forecasts(self, mock_get):
        """Cada dia da resposta vira um DailyForecast"""
        mock_get.return_value = build_response(build_open_meteo_payload())

        forecasts = OpenMeteoAdapter().fetch_daily_forecast(date(2026, 11, 21), date(2026, 11, 22))

        assert len(forecasts) == 2
        assert forecasts[0].day == date(2026, 11, 21)
        assert forecasts[0].description == "nublado"
        assert forecasts[0].temperature_min == 24.3
        assert forecasts[0].temperature_max == 31.3
        assert forecasts[0].precipitation_probability == 31
        assert forecasts[1].wind_max_kmh == 16.0

    @patch("adapters.open_meteo_adapter.requests.get")
    def test_null_values_become_zero(self, mock_get):
        """Valor null na resposta vira 0 em vez de quebrar a conversao"""
        payload = build_open_meteo_payload()
        payload["daily"]["precipitation_probability_max"] = [None, 34]
        mock_get.return_value = build_response(payload)

        forecasts = OpenMeteoAdapter().fetch_daily_forecast(date(2026, 11, 21), date(2026, 11, 22))

        assert forecasts[0].precipitation_probability == 0

    @patch("adapters.open_meteo_adapter.requests.get")
    def test_sends_rio_coordinates_timezone_and_dates(self, mock_get):
        """A consulta usa as coordenadas do Rio, o fuso de Sao Paulo e as datas pedidas"""
        mock_get.return_value = build_response(build_open_meteo_payload())

        OpenMeteoAdapter().fetch_daily_forecast(date(2026, 11, 21), date(2026, 11, 22))

        params = mock_get.call_args[1]["params"]
        assert params["latitude"] == RIO_LATITUDE
        assert params["longitude"] == RIO_LONGITUDE
        assert params["timezone"] == TIMEZONE
        assert params["start_date"] == "2026-11-21"
        assert params["end_date"] == "2026-11-22"

    @patch("adapters.open_meteo_adapter.requests.get")
    def test_api_error_payload_returns_empty_list(self, mock_get):
        """Resposta de erro da API (ex: data fora do alcance) devolve lista vazia"""
        mock_get.return_value = build_response(
            {"error": True, "reason": "Parameter 'start_date' is out of allowed range"}
        )

        assert OpenMeteoAdapter().fetch_daily_forecast(date(2027, 1, 30), date(2027, 1, 31)) == []

    @patch("adapters.open_meteo_adapter.requests.get")
    def test_network_error_returns_empty_list(self, mock_get):
        """Falha de rede nao derruba a conversa: devolve lista vazia"""
        mock_get.side_effect = ConnectionError("sem internet")

        assert OpenMeteoAdapter().fetch_daily_forecast(date(2026, 11, 21), date(2026, 11, 21)) == []

"""
Ferramenta de previsao do tempo do agente (cidade do Rio de Janeiro)

As datas pedidas sao validadas aqui, antes de chamar o provedor: previsao so
existe de hoje ate MAX_FORECAST_DAYS a frente, e uma data fora disso vira uma
mensagem clara para o LLM em vez de uma chamada inutil a API.
"""

from datetime import date, timedelta
from typing import Callable, List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from domain.weather_forecast import DailyForecast
from graph.prompts import format_date_in_portuguese
from ports.weather_port import WeatherPort

# Alcance da previsao gratuita do Open-Meteo (hoje + 15 dias)
MAX_FORECAST_DAYS = 16
WEATHER_SOURCE_LINE = "Fonte: Open-Meteo (open-meteo.com, CC BY 4.0)"


class WeatherForecastInput(BaseModel):
    """Schema de entrada da ferramenta de previsao do tempo"""

    start_date: str = Field(
        description=(
            "Primeiro dia da previsão, no formato AAAA-MM-DD. Calcule a partir da "
            "data de hoje informada nas instruções."
        )
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Último dia da previsão (AAAA-MM-DD). Omita para um dia só.",
    )


def build_weather_forecast_tool(
    weather: WeatherPort, current_date_provider: Callable[[], date] = date.today
) -> StructuredTool:
    """Cria a ferramenta de previsao do tempo injetando a porta de clima"""

    def _fetch_weather_forecast(start_date: str, end_date: Optional[str] = None) -> str:
        today = current_date_provider()
        try:
            start_day = date.fromisoformat(start_date)
            end_day = date.fromisoformat(end_date) if end_date else start_day
        except ValueError:
            return "Data inválida: use o formato AAAA-MM-DD."

        range_problem = check_forecast_range(start_day, end_day, today)
        if range_problem:
            return range_problem

        return format_forecasts(weather.fetch_daily_forecast(start_day, end_day))

    return StructuredTool.from_function(
        func=_fetch_weather_forecast,
        name="fetch_weather_forecast",
        description=(
            "Previsão do tempo diária da cidade do Rio de Janeiro (uma previsão para "
            "a cidade, não por bairro): condição do céu, temperaturas, chance de "
            "chuva, vento e índice UV. Use quando a pergunta envolver clima, chuva, "
            "praia, passeio ao ar livre ou plano B. Alcança até {} dias à frente."
        ).format(MAX_FORECAST_DAYS),
        args_schema=WeatherForecastInput,
    )


def check_forecast_range(start_day: date, end_day: date, today: date) -> str:
    """Valida o periodo pedido; devolve a explicacao do problema ou string vazia se estiver ok"""
    last_forecast_day = today + timedelta(days=MAX_FORECAST_DAYS - 1)

    if end_day < start_day:
        return "Período inválido: a data final é anterior à inicial."
    if start_day < today:
        return "Só há previsão de hoje ({}) em diante.".format(format_date_in_portuguese(today))
    if end_day > last_forecast_day:
        return (
            "Ainda não há previsão para essa data: a previsão só vai até {}."
        ).format(format_date_in_portuguese(last_forecast_day))
    return ""


def format_forecasts(forecasts: List[DailyForecast]) -> str:
    """Formata a previsao com uma linha por dia e a fonte no final"""
    if not forecasts:
        return "Não foi possível consultar a previsão do tempo agora."

    lines = [_format_single_day(forecast) for forecast in forecasts]
    lines.append(WEATHER_SOURCE_LINE)
    return "\n".join(lines)


def _format_single_day(forecast: DailyForecast) -> str:
    """Formata a previsao de um dia em uma linha"""
    return (
        "{}: {}, {:.0f}–{:.0f} °C, chance de chuva {}%, {:.1f} mm, "
        "vento até {:.0f} km/h, UV {:.1f}"
    ).format(
        format_date_in_portuguese(forecast.day),
        forecast.description,
        forecast.temperature_min,
        forecast.temperature_max,
        forecast.precipitation_probability,
        forecast.precipitation_mm,
        forecast.wind_max_kmh,
        forecast.uv_index_max,
    )

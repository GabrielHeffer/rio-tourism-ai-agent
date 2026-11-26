"""
Adapter que implementa WeatherPort usando a API de previsao do Open-Meteo

O Open-Meteo nao exige chave: o plano gratuito (uso nao comercial) limita as
chamadas por endereco IP. Os dados sao CC BY 4.0, entao a fonte precisa ser
citada (feito pela tool de clima).
"""

import logging
from datetime import date
from typing import Dict, List, Optional

import requests

from domain.weather_forecast import DailyForecast
from ports.weather_port import WeatherPort

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
RIO_LATITUDE = -22.9068
RIO_LONGITUDE = -43.1729
TIMEZONE = "America/Sao_Paulo"
REQUEST_TIMEOUT_SECONDS = 10
DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "wind_speed_10m_max",
    "uv_index_max",
]

# Codigos de tempo da OMM (WMO) usados pelo Open-Meteo
WMO_WEATHER_DESCRIPTIONS = {
    0: "céu limpo",
    1: "predominantemente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "neblina",
    48: "neblina com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa forte",
    56: "garoa congelante fraca",
    57: "garoa congelante forte",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "grãos de neve",
    80: "pancadas de chuva fracas",
    81: "pancadas de chuva moderadas",
    82: "pancadas de chuva fortes",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoadas",
    96: "trovoadas com granizo fraco",
    99: "trovoadas com granizo forte",
}
UNKNOWN_WEATHER_DESCRIPTION = "condição não informada"


def describe_weather_code(weather_code: Optional[int]) -> str:
    """Traduz o codigo WMO para uma descricao em portugues"""
    return WMO_WEATHER_DESCRIPTIONS.get(weather_code, UNKNOWN_WEATHER_DESCRIPTION)


class OpenMeteoAdapter(WeatherPort):
    """Implementa WeatherPort com a previsao diaria do Open-Meteo para a cidade do Rio"""

    def fetch_daily_forecast(self, start_day: date, end_day: date) -> List[DailyForecast]:
        """Busca a previsao diaria; em caso de falha devolve lista vazia, sem derrubar a conversa"""
        logger.info("Consultando previsão do tempo: {} a {}".format(start_day, end_day))
        try:
            response = requests.get(
                OPEN_METEO_URL,
                params=_build_request_params(start_day, end_day),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            payload = response.json()
        except Exception as e:
            logger.warning("Falha ao consultar a previsão do tempo: {}".format(e))
            return []

        if payload.get("error"):
            logger.warning("Open-Meteo recusou a consulta: {}".format(payload.get("reason")))
            return []

        return _build_daily_forecasts(payload.get("daily") or {})


def _build_request_params(start_day: date, end_day: date) -> Dict:
    """Monta os parametros da consulta de previsao diaria para o Rio"""
    return {
        "latitude": RIO_LATITUDE,
        "longitude": RIO_LONGITUDE,
        "daily": ",".join(DAILY_FIELDS),
        "timezone": TIMEZONE,
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
    }


def _build_daily_forecasts(daily: Dict) -> List[DailyForecast]:
    """Converte os arrays por campo do Open-Meteo em uma previsao por dia"""
    forecasts = []
    for index, day_text in enumerate(daily.get("time") or []):
        forecasts.append(
            DailyForecast(
                day=date.fromisoformat(day_text),
                description=describe_weather_code(_read_value(daily, "weather_code", index)),
                temperature_min=float(_read_value(daily, "temperature_2m_min", index) or 0),
                temperature_max=float(_read_value(daily, "temperature_2m_max", index) or 0),
                precipitation_probability=int(_read_value(daily, "precipitation_probability_max", index) or 0),
                precipitation_mm=float(_read_value(daily, "precipitation_sum", index) or 0),
                wind_max_kmh=float(_read_value(daily, "wind_speed_10m_max", index) or 0),
                uv_index_max=float(_read_value(daily, "uv_index_max", index) or 0),
            )
        )
    return forecasts


def _read_value(daily: Dict, field: str, index: int):
    """Le o valor de um campo no dia indicado; campo ausente ou curto vira None"""
    values = daily.get(field) or []
    return values[index] if index < len(values) else None

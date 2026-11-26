"""
Testes unitarios para graph/prompts.py (data atual no prompt de sistema)
"""

from datetime import date

from graph.prompts import (
    TOURISM_AGENT_SYSTEM_PROMPT,
    build_current_date_context,
    format_date_in_portuguese,
)


class TestFormatDateInPortuguese:
    """Data por extenso em portugues, sem depender do locale do sistema"""

    def test_formats_weekday_day_month_and_year(self):
        """Segunda-feira, 12 de outubro de 2026"""
        assert format_date_in_portuguese(date(2026, 10, 12)) == "segunda-feira, 12 de outubro de 2026"

    def test_uses_accented_names(self):
        """Nomes com acento saem corretos (sabado, marco)"""
        assert format_date_in_portuguese(date(2026, 3, 7)) == "sábado, 7 de março de 2026"

    def test_sunday_is_last_weekday(self):
        """Domingo e o ultimo dia da semana (weekday 6 no Python)"""
        assert format_date_in_portuguese(date(2026, 10, 18)).startswith("domingo")


class TestBuildCurrentDateContext:
    """Trecho do prompt com a data de hoje"""

    def test_includes_formatted_date(self):
        """O trecho informa a data de hoje por extenso"""
        context = build_current_date_context(date(2026, 10, 12))

        assert "Data de hoje: segunda-feira, 12 de outubro de 2026." in context

    def test_warns_about_events_from_other_dates(self):
        """O trecho pede para comparar a data dos eventos da web com a data pedida"""
        context = build_current_date_context(date(2026, 10, 12))

        assert "nunca apresente um evento de outra data" in context

    def test_asks_to_state_interpretation_of_ambiguous_dates(self):
        """Datas ambiguas (fim de semana com ou sem sexta) devem ter a interpretacao dita e mantida"""
        context = build_current_date_context(date(2026, 10, 12))

        assert "diga qual interpretação você está usando" in context


class TestSystemPromptRules:
    """Regras do prompt de sistema aprendidas nos testes de conversa"""

    def test_forbids_building_links(self):
        """So links recebidos nas buscas podem ser citados"""
        assert "Nunca monte ou deduza um link" in TOURISM_AGENT_SYSTEM_PROMPT

    def test_treats_forecast_as_estimate_and_cites_open_meteo(self):
        """A previsao do tempo e apresentada como estimativa e com a fonte"""
        assert "Previsão é estimativa" in TOURISM_AGENT_SYSTEM_PROMPT
        assert "entre parênteses logo após os números: (Open-Meteo)" in TOURISM_AGENT_SYSTEM_PROMPT

    def test_greets_only_in_first_answer(self):
        """A saudacao nao se repete a cada resposta"""
        assert "Cumprimente só na primeira resposta" in TOURISM_AGENT_SYSTEM_PROMPT

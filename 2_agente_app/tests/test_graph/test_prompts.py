"""
Testes unitarios para graph/prompts.py (data atual no prompt de sistema)
"""

from datetime import date

from graph.prompts import build_current_date_context, format_date_in_portuguese


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

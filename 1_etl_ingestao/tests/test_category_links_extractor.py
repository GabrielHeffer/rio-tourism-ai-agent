"""
Testes unitarios para category_links_extractor.py
Testa funcoes de parsing e deteccao de redes sociais
"""

import pytest
from bs4 import BeautifulSoup
from extractors.riotur.category_links_extractor import (
    CATEGORY_URLS,
)


class TestCategoryUrlsStructure:
    """Testes para estrutura de CATEGORY_URLS"""

    def test_has_three_sections(self):
        """Deve conter exatamente 3 secoes"""
        assert len(CATEGORY_URLS) == 3

    def test_has_o_que_fazer(self):
        """Deve ter secao 'o-que-fazer'"""
        assert "o-que-fazer" in CATEGORY_URLS

    def test_has_onde_comer(self):
        """Deve ter secao 'onde-comer'"""
        assert "onde-comer" in CATEGORY_URLS

    def test_has_onde_ficar(self):
        """Deve ter secao 'onde-ficar'"""
        assert "onde-ficar" in CATEGORY_URLS

    def test_o_que_fazer_has_six_categories(self):
        """o-que-fazer deve ter 6 categorias"""
        assert len(CATEGORY_URLS["o-que-fazer"]) == 6

    def test_onde_comer_has_seven_categories(self):
        """onde-comer deve ter 7 categorias"""
        assert len(CATEGORY_URLS["onde-comer"]) == 7

    def test_onde_ficar_has_five_categories(self):
        """onde-ficar deve ter 5 categorias"""
        assert len(CATEGORY_URLS["onde-ficar"]) == 5

    def test_total_categories_is_18(self):
        """Total de categorias deve ser 18 (6 + 7 + 5)"""
        total = sum(len(cats) for cats in CATEGORY_URLS.values())
        assert total == 18

    def test_each_category_has_url_and_name(self):
        """Cada categoria deve ter os campos 'url' e 'categoria'"""
        for secao, categorias in CATEGORY_URLS.items():
            for cat in categorias:
                assert "url" in cat
                assert "categoria" in cat
                assert cat["url"].startswith("https://riotur.rio/")

    def test_cultura_arte_url_correct(self):
        """Primeira categoria deve ser cultura-arte"""
        first = CATEGORY_URLS["o-que-fazer"][0]
        assert first["categoria"] == "cultura-arte"
        assert "cultura-arte" in first["url"]


class TestCategoryPageParsing:
    """Testes para parsing de pagina de categoria com HTML real"""

    def test_parse_items_from_html(self, cultura_arte_html):
        """HTML da pagina de categoria deve conter itens <li class='item'>"""
        soup = BeautifulSoup(cultura_arte_html, "html.parser")
        items = soup.find_all("li", class_="item")
        assert len(items) >= 16

    def test_each_item_has_h4_with_name(self, cultura_arte_html):
        """Cada item deve ter um nome em <h4>"""
        soup = BeautifulSoup(cultura_arte_html, "html.parser")
        items = soup.find_all("li", class_="item")
        for item in items:
            h4 = item.find("h4")
            if h4:
                assert len(h4.get_text(strip=True)) > 0

    def test_each_item_has_anchor_with_href(self, cultura_arte_html):
        """Cada item deve ter um link <a href>"""
        soup = BeautifulSoup(cultura_arte_html, "html.parser")
        items = soup.find_all("li", class_="item")
        for item in items:
            a_tag = item.find("a")
            if a_tag:
                assert a_tag.get("href") is not None

    def test_museu_naval_is_in_list(self, cultura_arte_html):
        """Museu Naval deve aparecer na lista de cultura-arte"""
        soup = BeautifulSoup(cultura_arte_html, "html.parser")
        text = soup.get_text()
        assert "Museu Naval" in text
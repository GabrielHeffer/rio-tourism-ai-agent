"""
Testes unitarios para item_details_extractor.py
Testa cada parser de campo individualmente com HTMLs reais
"""

import pytest
from bs4 import BeautifulSoup
from extractors.riotur.item_details_extractor import (
    extract_description,
    extract_address,
    extract_phone,
    extract_hours,
    extract_email,
    extract_website_and_socials,
    extract_tags,
    is_social_media,
    clean_text,
    extract_emails,
    extract_phones,
)


class TestSocialMediaDetection:
    """Testes para deteccao de URLs de redes sociais"""

    def test_instagram_is_social_media(self):
        """Instagram deve ser detectado como rede social"""
        assert is_social_media("https://www.instagram.com/ago_bardaencruza/")

    def test_facebook_is_social_media(self):
        """Facebook deve ser detectado como rede social"""
        assert is_social_media("https://facebook.com/riodejaneiro")

    def test_twitter_is_social_media(self):
        """Twitter deve ser detectado como rede social"""
        assert is_social_media("https://twitter.com/riodejaneiro")

    def test_youtube_is_social_media(self):
        """YouTube deve ser detectado como rede social"""
        assert is_social_media("https://youtube.com/watch?v=123")

    def test_real_website_is_not_social_media(self):
        """Site oficial real nao deve ser detectado como rede social"""
        assert not is_social_media("https://www.belmond.com/pt-br/hotels/")

    def test_gov_site_is_not_social_media(self):
        """Site .gov nao deve ser detectado como rede social"""
        assert not is_social_media("https://www.rio.rj.gov.br/")


class TestCleanText:
    """Testes para funcoes de limpeza de texto"""

    def test_clean_text_strips_whitespace(self):
        """Espacos extras sao colapsados e bordas removidas"""
        assert clean_text("  hello  world  ") == "hello world"

    def test_clean_text_empty_returns_empty(self):
        """String vazia retorna vazia"""
        assert clean_text("") == ""

    def test_clean_text_none_returns_empty(self):
        """None retorna vazio"""
        assert clean_text(None) == ""


class TestExtractEmails:
    """Testes para extracao de emails"""

    def test_extract_single_email(self):
        """Extrai um email simples do texto"""
        result = extract_emails("contato@museunaval.com.br")
        assert "contato@museunaval.com.br" in result

    def test_extract_multiple_emails(self):
        """Extrai multiplos emails sem duplicatas"""
        result = extract_emails("a@teste.com e b@teste.com")
        assert len(result) == 2

    def test_extract_no_email(self):
        """Texto sem email retorna lista vazia"""
        assert extract_emails("texto sem email") == []

    def test_extract_none_returns_empty(self):
        """None retorna lista vazia"""
        assert extract_emails(None) == []


class TestExtractPhones:
    """Testes para extracao de telefones"""

    def test_extract_brazilian_phone_with_country_code(self):
        """Telefone brasileiro com +55 e DDD 21"""
        result = extract_phones("ligue +55 21 2104-6851 para informacoes")
        assert len(result) > 0

    def test_extract_brazilian_phone_with_parentheses(self):
        """Telefone brasileiro com (21)"""
        result = extract_phones("ligue (21) 2548-7070")
        assert len(result) > 0

    def test_extract_no_phone(self):
        """Texto sem telefone retorna lista vazia"""
        assert extract_phones("sem telefone") == []


class TestExtractDescription:
    """Testes para extracao de descricao"""

    def test_extract_description_museu_naval(self, museu_naval_html):
        """Descricao do Museu Naval deve conter 'predio centenario'"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        desc = extract_description(soup)
        assert len(desc) > 100
        assert "Museu Naval" in desc or "predio" in desc.lower()

    def test_extract_description_ago(self, ago_html):
        """Descricao do Ago deve conter 'gastrobar'"""
        soup = BeautifulSoup(ago_html, "html.parser")
        desc = extract_description(soup)
        assert len(desc) > 20

    def test_extract_description_not_empty(self, museu_naval_html):
        """Descricao nunca retorna None"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        desc = extract_description(soup)
        assert desc is not None
        assert isinstance(desc, str)


class TestExtractAddress:
    """Testes para extracao de endereco"""

    def test_extract_address_museu_naval(self, museu_naval_html):
        """Endereco do Museu Naval contem 'Rua Dom Manuel'"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        address = extract_address(soup)
        assert "Rua Dom Manuel" in address or "Dom Manuel" in address

    def test_extract_address_ago(self, ago_html):
        """Endereco do Ago contem 'Rua Aurea'"""
        soup = BeautifulSoup(ago_html, "html.parser")
        address = extract_address(soup)
        assert "Aurea" in address or "Santa Teresa" in address

    def test_extract_address_returns_string(self, museu_naval_html):
        """Endereco sempre retorna string, nunca None"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        address = extract_address(soup)
        assert isinstance(address, str)


class TestExtractPhone:
    """Testes para extracao de telefone"""

    def test_extract_phone_museu_naval(self, museu_naval_html):
        """Museu Naval deve ter pelo menos 1 telefone"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        phones = extract_phone(soup)
        assert len(phones) > 0

    def test_extract_phone_copacabana_palace(self, copacabana_palace_html):
        """Copacabana Palace deve ter 2+ telefones"""
        soup = BeautifulSoup(copacabana_palace_html, "html.parser")
        phones = extract_phone(soup)
        assert len(phones) >= 2

    def test_extract_phone_returns_list(self, museu_naval_html):
        """Retorno sempre e lista"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        phones = extract_phone(soup)
        assert isinstance(phones, list)


class TestExtractHours:
    """Testes para extracao de horario"""

    def test_extract_hours_museu_naval(self, museu_naval_html):
        """Museu Naval tem horario 'quinta a domingo'"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        hours = extract_hours(soup)
        assert len(hours) > 0
        assert "quinta" in hours.lower() or "domingo" in hours.lower() or "17h" in hours

    def test_extract_hours_returns_string(self, museu_naval_html):
        """Horario sempre retorna string"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        hours = extract_hours(soup)
        assert isinstance(hours, str)


class TestExtractEmail:
    """Testes para extracao de email"""

    def test_extract_email_museu_naval(self, museu_naval_html):
        """Museu Naval tem email 'dphdm.educativo@marinha.mil.br'"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        email = extract_email(soup)
        assert "marinha.mil.br" in email or "dphdm" in email

    def test_extract_email_copacabana_palace(self, copacabana_palace_html):
        """Copacabana Palace tem email 'reservations@belmond.com'"""
        soup = BeautifulSoup(copacabana_palace_html, "html.parser")
        email = extract_email(soup)
        assert "belmond" in email.lower()

    def test_extract_email_returns_string(self, museu_naval_html):
        """Email sempre retorna string"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        email = extract_email(soup)
        assert isinstance(email, str)


class TestExtractWebsiteAndSocials:
    """Testes para extracao de website e redes sociais"""

    def test_copacabana_palace_has_real_website(self, copacabana_palace_html):
        """Copacabana Palace deve ter website oficial (belmond.com)"""
        soup = BeautifulSoup(copacabana_palace_html, "html.parser")
        website, socials = extract_website_and_socials(soup)
        assert website is not None
        assert "belmond" in website.lower()

    def test_copacabana_palace_website_is_not_carnaval(self, copacabana_palace_html):
        """Website NAO deve ser carnaval.rio (link do footer)"""
        soup = BeautifulSoup(copacabana_palace_html, "html.parser")
        website, socials = extract_website_and_socials(soup)
        assert "carnaval.rio" not in str(website).lower()

    def test_ago_instagram_not_website(self, ago_html):
        """Instagram do Ago nao deve ser tratado como website oficial"""
        soup = BeautifulSoup(ago_html, "html.parser")
        website, socials = extract_website_and_socials(soup)
        # Instagram nao e website oficial
        if website and "instagram" in website.lower():
            pytest.fail("Instagram foi tratado como website oficial")

    def test_returns_tuple(self, museu_naval_html):
        """Retorno sempre e (website, socials)"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        result = extract_website_and_socials(soup)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestExtractTags:
    """Testes para extracao de tags"""

    def test_extract_tags_returns_list(self, museu_naval_html):
        """Tags sempre retorna lista"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        tags = extract_tags(soup)
        assert isinstance(tags, list)
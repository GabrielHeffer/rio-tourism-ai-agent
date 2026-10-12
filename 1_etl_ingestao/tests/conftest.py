"""
Fixtures compartilhadas para os testes do pipeline ETL
HTMLs reais salvos em tests/fixtures/
"""

import sys
from pathlib import Path
import pytest

# Garante que o módulo 1_etl_ingestao está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ═══════════════════════════════════════════════════════════════════════════
# HTML Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cultura_arte_html():
    """HTML real da pagina de categoria Cultura e Arte (16 itens estaticos)"""
    return (FIXTURES_DIR / "categoria_cultura_arte.html").read_text(encoding="utf-8")

@pytest.fixture
def museu_naval_html():
    """HTML real da pagina de detalhe do Museu Naval"""
    return (FIXTURES_DIR / "detalhe_museu_naval.html").read_text(encoding="utf-8")

@pytest.fixture
def ago_html():
    """HTML real da pagina do Ago (restaurante, Instagram como website)"""
    return (FIXTURES_DIR / "detalhe_ago.html").read_text(encoding="utf-8")

@pytest.fixture
def copacabana_palace_html():
    """HTML real da pagina do Copacabana Palace (com site oficial real)"""
    return (FIXTURES_DIR / "detalhe_copacabana_palace.html").read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# Item Fixtures (simulam saida do Asset 2: riotur_item_details)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def museu_naval_item():
    """Item com todos os campos preenchidos (o-que-fazer)"""
    return {
        "nome": "Museu Naval",
        "descricao": "Localizado em um predio centenario no Centro do Rio, o Museu Naval conta com um acervo que inclui modelos navais, obras de arte, canhoes resgatados de navios naufragados, figuras de proa, medalhas e documentos historicos.",
        "endereco": "Rua Dom Manuel, 15 - CentroRio de Janeiro - RJ20010090, +55 21 2104-6851+55#Museu#Museu NavalTAGS",
        "telefones": ["+55 21 2104-6851", "21 2104-6851"],
        "horario": "quinta a domingo, das 13h as 17h",
        "email": "dphdm.educativo@marinha.mil.br",
        "website_oficial": None,
        "redes_sociais": [],
        "tags": [],
        "secao": "o-que-fazer",
        "categoria": "cultura-arte",
        "subcategoria": "Cultura e Arte",
        "url_riotur": "https://riotur.rio/que_fazer/museu-naval/",
        "imagem_url": "https://riotur.rio/wp-content/uploads/2024/12/IMG_1667-1-250x250.jpg",
        "data_extracao": "2026-08-18T18:37:30"
    }

@pytest.fixture
def ago_item():
    """Item de restaurante com Instagram no campo website"""
    return {
        "nome": "Ago",
        "descricao": "O gastrobar apresenta um cardapio que reune pratos que bebem dos ensinamentos do candomble e umbanda.",
        "endereco": "Rua Aurea, 30 - Santa TeresaRio de Janeiro - RJ",
        "telefones": [],
        "horario": "",
        "email": "imprensa.riotur@gmail.com",
        "website_oficial": None,
        "redes_sociais": [
            {"rede": "Instagram", "url": "https://www.instagram.com/ago_bardaencruza/"}
        ],
        "tags": [],
        "secao": "onde-comer",
        "categoria": "restaurantes",
        "subcategoria": "Restaurantes",
        "url_riotur": "https://riotur.rio/onde_comer/ago/",
        "imagem_url": "",
        "data_extracao": "2026-08-18T18:37:30"
    }

@pytest.fixture
def copacabana_palace_item():
    """Item de hotel com website oficial real"""
    return {
        "nome": "Copacabana Palace",
        "descricao": "Copacabana nao seria a mesma sem o maior icone da orla.",
        "endereco": "Av. Atlantica, 1702 - CopacabanaRio de Janeiro - RJ",
        "telefones": ["+55 21 2548 7070", "21 2548 7070"],
        "horario": "",
        "email": "reservations.brazil@belmond.com",
        "website_oficial": "https://www.belmond.com/pt-br/hotels/south-america/brazil/rio-de-janeiro/belmond-copacabana-palace/",
        "redes_sociais": [],
        "tags": [],
        "secao": "onde-ficar",
        "categoria": "hoteis",
        "subcategoria": "Hoteis",
        "url_riotur": "https://riotur.rio/onde_ficar/copacabana-palace-2/",
        "imagem_url": "https://riotur.rio/wp-content/uploads/2016/09/50122291748_85f43be999_k-500x500.jpg",
        "data_extracao": "2026-08-18T18:37:30"
    }

@pytest.fixture
def empty_item():
    """Item com campos vazios (caso extremo)"""
    return {
        "nome": "Item Vazio",
        "descricao": "",
        "endereco": "",
        "telefones": [],
        "horario": "",
        "email": "",
        "website_oficial": None,
        "redes_sociais": [],
        "tags": [],
        "secao": "desconhecida",
        "categoria": "teste",
        "subcategoria": None,
        "url_riotur": "https://riotur.rio/teste/",
        "imagem_url": "",
        "data_extracao": "2026-08-18T18:37:30"
    }


# ═══════════════════════════════════════════════════════════════════════════
# Document Fixtures (simulam saida do Asset 3: riotur_documents)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_documents():
    """Lista de 3 documentos prontos para testar loader"""
    return [
        {
            "id": "cultura-arte-museu-naval",
            "document": "Museu Naval e um ponto turistico no Rio de Janeiro. Localizado no Centro, funciona de quinta a domingo. Telefone: +55 21 2104-6851",
            "metadata": {
                "nome": "Museu Naval",
                "secao": "o-que-fazer",
                "categoria": "cultura-arte",
                "endereco": "Rua Dom Manuel, 15 - Centro",
                "telefone": "+55 21 2104-6851",
                "horario": "quinta a domingo, das 13h as 17h",
                "website": ""
            }
        },
        {
            "id": "restaurantes-ago",
            "document": "Ago e um restaurante no Rio de Janeiro. Localizado em Santa Teresa.",
            "metadata": {
                "nome": "Ago",
                "secao": "onde-comer",
                "categoria": "restaurantes",
                "endereco": "Rua Aurea, 30 - Santa Teresa",
                "telefone": "",
                "horario": "",
                "website": ""
            }
        },
        {
            "id": "hoteis-copacabana-palace",
            "document": "Copacabana Palace e uma hospedagem no Rio de Janeiro. Website: https://www.belmond.com/",
            "metadata": {
                "nome": "Copacabana Palace",
                "secao": "onde-ficar",
                "categoria": "hoteis",
                "endereco": "Av. Atlantica, 1702 - Copacabana",
                "telefone": "+55 21 2548 7070",
                "horario": "",
                "website": "https://www.belmond.com/"
            }
        }
    ]
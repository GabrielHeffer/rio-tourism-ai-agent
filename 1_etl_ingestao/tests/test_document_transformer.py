"""
Testes unitarios para document_transformer.py
Testa limpeza de dados e templates de geracao de documentos
"""

import pytest
from document_transformer import (
    clean_text,
    clean_description,
    clean_address,
    clean_phone_list,
    format_phone_list,
    generate_document_o_que_fazer,
    generate_document_onde_comer,
    generate_document_onde_ficar,
    generate_document,
    transform_items_to_documents,
    extract_social_media_text,
)


class TestCleanText:
    """Testes para clean_text"""

    def test_strips_leading_trailing_spaces(self):
        """Remove espacos do inicio e fim"""
        assert clean_text("  hello  ") == "hello"

    def test_collapses_multiple_spaces(self):
        """Multiplos espacos viram um"""
        assert clean_text("a   b   c") == "a b c"

    def test_removes_null_bytes(self):
        """Remove caracteres de controle (null byte)"""
        result = clean_text("texto\x00com\x1Fcontrole")
        assert "\x00" not in result

    def test_empty_string(self):
        """String vazia retorna vazia"""
        assert clean_text("") == ""

    def test_none_input(self):
        """None retorna vazio"""
        assert clean_text(None) == ""


class TestCleanDescription:
    """Testes para clean_description (rodape do site e marcas de nota)"""

    RODAPE = (
        "Para entrar em contato conosco, envie um e-mail para "
        "imprensa.riotur@gmail.com ou preencha o formulário abaixo."
    )

    def test_removes_site_footer(self):
        """Rodape institucional do RioTur sai da descricao"""
        result = clean_description("Quiosque com chopp gelado. " + self.RODAPE)
        assert result == "Quiosque com chopp gelado."

    def test_removes_footer_with_city_hall_signature(self):
        """Assinatura da prefeitura que segue o rodape tambem sai"""
        texto = "Museu no Centro. " + self.RODAPE + " Prefeito Eduardo Paes Presidente Bernardo Fellows"
        assert clean_description(texto) == "Museu no Centro."

    def test_removes_footnote_asterisks(self):
        """Asterisco de nota nao vai para o documento"""
        result = clean_description("de sexta a domingo, tem show* MPB ao vivo")
        assert result == "de sexta a domingo, tem show MPB ao vivo"

    def test_keeps_description_without_footer(self):
        """Descricao sem rodape nao e alterada"""
        assert clean_description("Talharim e calabresa.") == "Talharim e calabresa."

    def test_none_returns_empty(self):
        """None retorna string vazia"""
        assert clean_description(None) == ""


class TestCleanAddress:
    """Testes para clean_address"""

    def test_removes_phone_numbers(self):
        """Telefone misturado no endereco e removido"""
        dirty = "Rua X, 123, +55 21 9999-9999"
        result = clean_address(dirty)
        assert "+55" not in result

    def test_removes_website_urls(self):
        """Website misturado no endereco e removido"""
        dirty = "Rua X, 123, https://www.site.com"
        result = clean_address(dirty)
        assert "http" not in result

    def test_removes_email_addresses(self):
        """Email misturado no endereco e removido"""
        dirty = "Rua X, 123, contato@email.com"
        result = clean_address(dirty)
        assert "@" not in result

    def test_removes_tags_keyword(self):
        """Keyword 'TAGS' e removida do endereco"""
        dirty = "Rua X, 123, #Museu#NavalTAGS"
        result = clean_address(dirty)
        assert "TAGS" not in result

    def test_removes_endereco_keyword(self):
        """Keyword 'ENDERECO' e removida do endereco"""
        dirty = "ENDERECO Rua X, 123"
        result = clean_address(dirty)
        assert "ENDERECO" not in result

    def test_empty_returns_empty(self):
        """Endereco vazio retorna vazio"""
        assert clean_address("") == ""

    def test_none_returns_empty(self):
        """None retorna vazio"""
        assert clean_address(None) == ""


class TestFormatPhoneList:
    """Testes para format_phone_list"""

    def test_single_phone(self):
        """Um unico telefone retorna ele mesmo"""
        result = format_phone_list(["+55 21 2104-6851"])
        assert "+55 21 2104-6851" in result

    def test_two_phones(self):
        """Dois telefones sao separados por 'ou'"""
        result = format_phone_list(["+55 21 2104-6851", "21 2104-6851"])
        assert " ou " in result

    def test_empty_list_returns_empty(self):
        """Lista vazia retorna string vazia"""
        assert format_phone_list([]) == ""

    def test_none_returns_empty(self):
        """None retorna string vazia"""
        assert format_phone_list(None) == ""

    def test_deduplicates(self):
        """Telefones duplicados sao removidos"""
        result = format_phone_list(["21 2104", "21 2104"])
        assert result.count("2104") == 1


class TestExtractSocialMediaText:
    """Testes para extract_social_media_text"""

    def test_instagram_only(self):
        """So Instagram retorna 'Instagram'"""
        socials = [{"rede": "Instagram", "url": "https://..."}]
        result = extract_social_media_text(socials)
        assert "Instagram" in result

    def test_two_socials(self):
        """Duas redes retornam 'E' entre elas"""
        socials = [
            {"rede": "Instagram", "url": "..."},
            {"rede": "Facebook", "url": "..."},
        ]
        result = extract_social_media_text(socials)
        assert "Instagram" in result
        assert "Facebook" in result

    def test_empty_returns_empty(self):
        """Lista vazia retorna string vazia"""
        assert extract_social_media_text([]) == ""


class TestGenerateDocumentOQueFazer:
    """Testes para template de o-que-fazer"""

    def test_contains_name(self, museu_naval_item):
        """Documento contem o nome do item"""
        doc = generate_document_o_que_fazer(museu_naval_item)
        assert "Museu Naval" in doc

    def test_contains_section_type(self, museu_naval_item):
        """Documento contem a subcategoria"""
        doc = generate_document_o_que_fazer(museu_naval_item)
        assert "cultura e arte" in doc.lower()

    def test_nao_embute_bloco_de_contato(self, museu_naval_item):
        """Endereco, telefone e horario ficam fora do texto que vira vetor.

        Eles continuam no metadata, de onde o agente os le para exibir. Dentro do
        embedding um CEP ou DDD so ocupa a janela do modelo e dilui o sinal.
        """
        doc = generate_document_o_que_fazer(museu_naval_item)

        assert "Endere" not in doc
        assert "Telefone" not in doc
        assert "2104-6851" not in doc

    def test_nao_embute_boilerplate_da_cidade(self, museu_naval_item):
        """A base inteira e do Rio: repetir a cidade em todo documento e ruido"""
        doc = generate_document_o_que_fazer(museu_naval_item)

        assert "no Rio de Janeiro" not in doc

    def test_cabecalho_tem_nome_tipo_e_bairro(self, museu_naval_item):
        """O cabecalho concentra o que discrimina o lugar"""
        doc = generate_document_o_que_fazer(museu_naval_item)

        assert doc.startswith("Museu Naval.")
        assert "Centro" in doc

    def test_empty_item_does_not_crash(self, empty_item):
        """Item vazio gera documento minimo, nao lanca excecao"""
        doc = generate_document_o_que_fazer(empty_item)
        assert isinstance(doc, str)
        assert len(doc) > 0


class TestGenerateDocumentOndeComer:
    """Testes para template de onde-comer"""

    def test_contains_name(self, ago_item):
        """Documento contem o nome do item"""
        doc = generate_document_onde_comer(ago_item)
        assert "Ago" in doc

    def test_no_hours_field(self, ago_item):
        """Template de restaurante nao tem campo horario (opcional)"""
        doc = generate_document_onde_comer(ago_item)
        # Horario nao e campo obrigatorio para restaurantes
        assert isinstance(doc, str)

    def test_nao_embute_redes_sociais(self, ago_item):
        """Redes sociais ficam no metadata, fora do texto embutido"""
        doc = generate_document_onde_comer(ago_item)
        assert "Instagram" not in doc

    def test_empty_item_does_not_crash(self, empty_item):
        """Item vazio gera documento minimo"""
        doc = generate_document_onde_comer(empty_item)
        assert isinstance(doc, str)
        assert len(doc) > 0


class TestGenerateDocumentOndeFicar:
    """Testes para template de onde-ficar"""

    def test_contains_name(self, copacabana_palace_item):
        """Documento contem o nome do item"""
        doc = generate_document_onde_ficar(copacabana_palace_item)
        assert "Copacabana Palace" in doc

    def test_nao_embute_website_nem_telefone(self, copacabana_palace_item):
        """URL e telefone ficam fora do texto embutido; seguem no metadata"""
        doc = generate_document_onde_ficar(copacabana_palace_item)

        assert "belmond.com" not in doc
        assert "2548 7070" not in doc

    def test_contato_continua_disponivel_no_metadata(self, copacabana_palace_item):
        """Tirar do embedding nao pode perder o dado para exibicao"""
        documentos = transform_items_to_documents([copacabana_palace_item])

        metadata = documentos[0]["metadata"]
        assert "2548 7070" in metadata["telefone"]
        assert "belmond.com" in metadata["website"]

    def test_empty_item_does_not_crash(self, empty_item):
        """Item vazio gera documento minimo"""
        doc = generate_document_onde_ficar(empty_item)
        assert isinstance(doc, str)
        assert len(doc) > 0


class TestGenerateDocumentDispatcher:
    """Testes para o dispatcher generate_document"""

    def test_dispatches_o_que_fazer(self, museu_naval_item):
        """Seleciona template o-que-fazer pela secao"""
        doc = generate_document(museu_naval_item)
        assert "Museu Naval" in doc

    def test_dispatches_onde_comer(self, ago_item):
        """Seleciona template onde-comer pela secao"""
        doc = generate_document(ago_item)
        assert "Ago" in doc

    def test_dispatches_onde_ficar(self, copacabana_palace_item):
        """Seleciona template onde-ficar pela secao"""
        doc = generate_document(copacabana_palace_item)
        assert "Copacabana Palace" in doc

    def test_unknown_section_fallback(self, empty_item):
        """Secao desconhecida gera documento usando template padrao"""
        doc = generate_document(empty_item)
        assert isinstance(doc, str)
        assert len(doc) > 0


class TestTransformItemsToDocuments:
    """Testes para transform_items_to_documents"""

    def test_transforms_multiple_items(self, museu_naval_item, ago_item, copacabana_palace_item):
        """Multiplos itens geram multiplos documentos"""
        items = [museu_naval_item, ago_item, copacabana_palace_item]
        docs = transform_items_to_documents(items)
        assert len(docs) == 3

    def test_each_document_has_id(self, museu_naval_item):
        """Cada documento tem um id unico"""
        docs = transform_items_to_documents([museu_naval_item])
        assert "id" in docs[0]
        assert len(docs[0]["id"]) > 0

    def test_each_document_has_metadata(self, museu_naval_item):
        """Cada documento tem metadados"""
        docs = transform_items_to_documents([museu_naval_item])
        assert "metadata" in docs[0]
        assert docs[0]["metadata"]["nome"] == "Museu Naval"

    def test_each_document_has_text(self, museu_naval_item):
        """Cada documento tem texto"""
        docs = transform_items_to_documents([museu_naval_item])
        assert "document" in docs[0]
        assert len(docs[0]["document"]) > 0

    def test_empty_item_is_skipped(self, empty_item):
        """Item com nome minimo gera documento basico"""
        docs = transform_items_to_documents([empty_item])
        # Pode gerar documento minimo com apenas o nome
        assert len(docs) >= 0

    def test_empty_list_returns_empty(self):
        """Lista vazia retorna lista vazia"""
        docs = transform_items_to_documents([])
        assert docs == []


class TestMetadataSemNone:
    """Regressao: ChromaDB recusa None em metadata e derrubou 17 de 21 batches"""

    def test_website_none_vira_string_vazia(self, museu_naval_item):
        """website_oficial=None nao pode chegar como None no metadata"""
        item = dict(museu_naval_item)
        item["website_oficial"] = None

        docs = transform_items_to_documents([item])

        assert docs[0]["metadata"]["website"] == ""

    def test_nenhum_campo_de_metadata_e_none(self, museu_naval_item):
        """Qualquer campo None do extractor e normalizado, nao so website"""
        item = dict(museu_naval_item)
        for campo in ("website_oficial", "email", "horario", "endereco", "subcategoria"):
            item[campo] = None

        docs = transform_items_to_documents([item])

        nulos = [k for k, v in docs[0]["metadata"].items() if v is None]
        assert nulos == []


class TestIdsUnicos:
    """Regressao: ids repetidos fazem o ChromaDB recusar o batch inteiro"""

    def test_descarta_documento_com_id_duplicado(self, museu_naval_item):
        """Mesmo nome e categoria geram o mesmo id: so o primeiro entra"""
        docs = transform_items_to_documents([museu_naval_item, dict(museu_naval_item)])

        assert len(docs) == 1

    def test_ids_da_lista_sao_unicos(self, museu_naval_item, ago_item, copacabana_palace_item):
        """A lista devolvida nunca tem id repetido"""
        items = [museu_naval_item, ago_item, copacabana_palace_item, dict(ago_item)]

        docs = transform_items_to_documents(items)

        ids = [d["id"] for d in docs]
        assert len(ids) == len(set(ids))

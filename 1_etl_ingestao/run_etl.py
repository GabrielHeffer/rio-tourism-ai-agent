"""
Orquestrador do pipeline ETL - RioTur
Define assets Dagster para extracao de dados
"""

import json
from pathlib import Path
import dagster as dg
from extractors.riotur.category_links_extractor import extract_all_categories_sync
from extractors.riotur.item_details_extractor import extract_all_items_details
from document_transformer import transform_items_to_documents
from loader import load_documents_to_chromadb, get_chromadb_stats

# Raiz do projeto: 1_etl_ingestao/ fica um nivel abaixo dela. O Dagster obriga rodar
# de dentro desta pasta (os imports acima sao relativos a ela), entao um Path("data_raw")
# solto criaria 1_etl_ingestao/data_raw/ em vez do data_raw/ compartilhado da raiz.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data_raw"


@dg.asset(
    name="riotur_category_links",
    description="Extrai todos os links de categorias do RioTur usando Playwright",
    tags={"layer": "raw", "source": "riotur.rio"},
)
def riotur_category_links(context: dg.AssetExecutionContext) -> list[dict]:
    """
    Asset Dagster que:
    1. Visita as 18 categorias do RioTur
    2. Clica em "ver mais" ate carregar todos os itens
    3. Extrai nome, categoria, URL e imagem de cada item
    4. Salva em data_raw/riotur_links.json
    5. Retorna a lista completa para proximas transformacoes

    Returns:
        Lista de dicts com estrutura:
        {
            "nome": str,
            "subcategoria": str,
            "secao": str (o-que-fazer, onde-comer, onde-ficar),
            "categoria": str,
            "url": str,
            "imagem_url": str
        }
    """
    context.log.info("[*] Iniciando extracao de links de categorias do RioTur...")

    try:
        # Executa a extracao
        all_links = extract_all_categories_sync()

        # Salva em JSON
        data_raw_path = DATA_RAW
        data_raw_path.mkdir(exist_ok=True)

        output_file = data_raw_path / "riotur_links.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_links, f, ensure_ascii=False, indent=2)

        context.log.info("[OK] {} links salvos em {}".format(len(all_links), output_file))

        # Log por secao
        secoes = {}
        for link in all_links:
            secao = link["secao"]
            if secao not in secoes:
                secoes[secao] = 0
            secoes[secao] += 1

        for secao, count in sorted(secoes.items()):
            context.log.info("  * {}: {} itens".format(secao, count))

        return all_links

    except Exception as e:
        context.log.error("[ERRO] Falha ao extrair links: {}".format(e))
        raise


@dg.asset(
    name="riotur_item_details",
    description="Extrai detalhes de cada item (descricao, endereco, telefone, etc)",
    tags={"layer": "raw", "source": "riotur.rio"},
    deps=[riotur_category_links]
)
def riotur_item_details(context: dg.AssetExecutionContext, riotur_category_links: list[dict]) -> list[dict]:
    """
    Asset Dagster que:
    1. Para cada URL coletada em riotur_category_links
    2. Faz requisicao da pagina de detalhe
    3. Extrai: descricao, endereco, telefone, horario, email, website, redes sociais, tags
    4. Salva em data_raw/riotur_details.json
    5. Retorna lista com todos os detalhes

    Depende de: riotur_category_links
    
    Returns:
        Lista de dicts com estrutura:
        {
            "nome": str,
            "descricao": str,
            "endereco": str,
            "telefones": [str],
            "horario": str,
            "email": str,
            "website_oficial": str or null,
            "redes_sociais": [{rede, url}],
            "tags": [str],
            "secao": str,
            "categoria": str,
            "url_riotur": str,
            "imagem_url": str,
            "data_extracao": str
        }
    """
    context.log.info("[*] Iniciando extracao de detalhes de {} itens...".format(len(riotur_category_links)))

    try:
        # Executa a extracao
        all_details = extract_all_items_details(riotur_category_links)

        # Salva em JSON
        data_raw_path = DATA_RAW
        data_raw_path.mkdir(exist_ok=True)

        output_file = data_raw_path / "riotur_details.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_details, f, ensure_ascii=False, indent=2)

        context.log.info("[OK] {} detalhes salvos em {}".format(len(all_details), output_file))

        # Estatisticas
        com_website = sum(1 for d in all_details if d.get("website_oficial"))
        com_redes = sum(1 for d in all_details if d.get("redes_sociais"))
        com_telefone = sum(1 for d in all_details if d.get("telefones"))
        com_horario = sum(1 for d in all_details if d.get("horario"))
        com_erro = sum(1 for d in all_details if "erro" in d)

        context.log.info("  * Com website oficial: {}".format(com_website))
        context.log.info("  * Com redes sociais: {}".format(com_redes))
        context.log.info("  * Com telefone: {}".format(com_telefone))
        context.log.info("  * Com horario: {}".format(com_horario))
        context.log.info("  * Com erro: {}".format(com_erro))

        return all_details

    except Exception as e:
        context.log.error("[ERRO] Falha ao extrair detalhes: {}".format(e))
        raise


@dg.asset(
    name="riotur_documents",
    description="Transforma detalhes em documentos de texto para embeddings",
    tags={"layer": "intermediate", "source": "riotur.rio"},
    deps=[riotur_item_details]
)
def riotur_documents(context: dg.AssetExecutionContext, riotur_item_details: list[dict]) -> list[dict]:
    """
    Asset Dagster que:
    1. Recebe detalhes de cada item
    2. Limpa dados sujos (enderecos duplicados, etc)
    3. Transforma em texto corrido (linguagem natural)
    4. Prepara metadados estruturados
    5. Salva em data_raw/riotur_documents.json
    6. Retorna documentos prontos para embeddings

    Depende de: riotur_item_details
    
    Returns:
        Lista de dicts com estrutura:
        {
            "id": str (identificador unico),
            "document": str (texto em linguagem natural),
            "metadata": dict (dados estruturados)
        }
    """
    context.log.info("[*] Transformando {} itens em documentos...".format(len(riotur_item_details)))

    try:
        # Executa transformacao
        documents = transform_items_to_documents(riotur_item_details)

        # Salva em JSON
        data_raw_path = DATA_RAW
        data_raw_path.mkdir(exist_ok=True)

        output_file = data_raw_path / "riotur_documents.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

        context.log.info("[OK] {} documentos salvos em {}".format(len(documents), output_file))

        # Estatisticas
        por_secao = {}
        for doc in documents:
            secao = doc["metadata"].get("secao", "desconhecido")
            if secao not in por_secao:
                por_secao[secao] = 0
            por_secao[secao] += 1

        for secao, count in sorted(por_secao.items()):
            context.log.info("  * {}: {} documentos".format(secao, count))

        return documents

    except Exception as e:
        context.log.error("[ERRO] Falha ao transformar documentos: {}".format(e))
        raise


@dg.asset(
    name="chromadb_turismo_rio",
    description="Carrega documentos em ChromaDB com embeddings",
    tags={"layer": "warehouse", "source": "chromadb"},
    deps=[riotur_documents]
)
def chromadb_turismo_rio(context: dg.AssetExecutionContext, riotur_documents: list[dict]) -> dict:
    """
    Asset Dagster que:
    1. Recebe documentos transformados
    2. Carrega em ChromaDB com embeddings
    3. Cria indices para busca semantica
    4. Retorna estatisticas

    Depende de: riotur_documents
    
    Returns:
        Dict com estatisticas de carregamento
    """
    context.log.info("[*] Carregando {} documentos em ChromaDB...".format(len(riotur_documents)))

    try:
        # Carrega em ChromaDB
        collection = load_documents_to_chromadb(riotur_documents)

        # Obtem stats
        stats = get_chromadb_stats()
        stats["documentos_carregados"] = len(riotur_documents)

        # Guarda contra "sucesso mentiroso": a carga pode falhar batch a batch e ainda assim
        # retornar normalmente. Sem esta checagem o asset materializa sobre uma base vazia.
        total_no_banco = stats.get("total_documentos", 0)
        if riotur_documents and total_no_banco == 0:
            raise RuntimeError(
                "[ERRO] Carga concluiu mas ChromaDB esta vazio: {} documentos enviados, "
                "{} no banco (status: {}). Veja os logs de shared.vector_store.".format(
                    len(riotur_documents), total_no_banco, stats.get("status"))
            )

        context.log.info("[OK] ChromaDB atualizado com sucesso")
        context.log.info("  * Total de documentos: {}".format(stats.get("total_documentos", 0)))
        context.log.info("  * Status: {}".format(stats.get("status", "desconhecido")))

        return stats

    except Exception as e:
        context.log.exception("[ERRO] Falha ao carregar em ChromaDB: {}".format(e))
        raise


# Definicoes Dagster
defs = dg.Definitions(assets=[riotur_category_links, riotur_item_details, riotur_documents, chromadb_turismo_rio])


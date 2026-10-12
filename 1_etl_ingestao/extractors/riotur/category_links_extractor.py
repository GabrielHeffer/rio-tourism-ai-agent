"""
Extrator de URLs de Categorias do RioTur.Rio
Usa Playwright para navegar e carregar todas as páginas via "ver mais"
"""

import logging
import asyncio
from typing import List, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError

# Configuração de logging: modulo de biblioteca nao configura o root logger.
# Quem executa decide (o Dagster faz isso via managed_python_loggers no dagster.yaml).
logger = logging.getLogger(__name__)

# Mensagem exibida quando o Chromium do Playwright nao foi baixado para esta venv
BROWSER_MISSING_MSG = (
    "[ERRO] Chromium do Playwright nao encontrado nesta venv. "
    "Rode: poetry run playwright install chromium "
    "(browsers instalados por outra versao do Playwright nao servem: "
    "o projeto usa playwright==1.50.0)"
)

# URLs de todas as 18 categorias agrupadas por seção
CATEGORY_URLS = {
    "o-que-fazer": [
        {
            "url": "https://riotur.rio/o-que-fazer/cultura-arte/",
            "categoria": "cultura-arte",
        },
        {
            "url": "https://riotur.rio/o-que-fazer/ao-ar-livre/",
            "categoria": "ao-ar-livre",
        },
        {
            "url": "https://riotur.rio/o-que-fazer/comercio/",
            "categoria": "comercio",
        },
        {
            "url": "https://riotur.rio/o-que-fazer/esportes/",
            "categoria": "esportes",
        },
        {
            "url": "https://riotur.rio/o-que-fazer/agencias-e-guias-de-turismo/",
            "categoria": "agencias-e-guias-de-turismo",
        },
        {
            "url": "https://riotur.rio/o-que-fazer/vida-noturna/",
            "categoria": "vida-noturna",
        },
    ],
    "onde-comer": [
        {
            "url": "https://riotur.rio/onde-comer/cafeterias/",
            "categoria": "cafeterias",
        },
        {
            "url": "https://riotur.rio/onde-comer/churrascaria/",
            "categoria": "churrascaria",
        },
        {
            "url": "https://riotur.rio/onde-comer/botecos/",
            "categoria": "botecos",
        },
        {
            "url": "https://riotur.rio/onde-comer/premiados/",
            "categoria": "premiados",
        },
        {
            "url": "https://riotur.rio/onde-comer/quiosques/",
            "categoria": "quiosques",
        },
        {
            "url": "https://riotur.rio/onde-comer/restaurantes/",
            "categoria": "restaurantes",
        },
        {
            "url": "https://riotur.rio/onde-comer/polos-gastronomicos/",
            "categoria": "polos-gastronomicos",
        },
    ],
    "onde-ficar": [
        {
            "url": "https://riotur.rio/onde-ficar/albergues/",
            "categoria": "albergues",
        },
        {
            "url": "https://riotur.rio/onde-ficar/apart-hoteis/",
            "categoria": "apart-hoteis",
        },
        {
            "url": "https://riotur.rio/onde-ficar/cama-e-cafe/",
            "categoria": "cama-e-cafe",
        },
        {
            "url": "https://riotur.rio/onde-ficar/hoteis/",
            "categoria": "hoteis",
        },
        {
            "url": "https://riotur.rio/onde-ficar/pousada/",
            "categoria": "pousada",
        },
    ],
}


async def extract_category_links(
    page, url: str, secao: str, categoria: str
) -> List[Dict]:
    """
    Extrai todos os links de uma categoria específica usando Playwright.
    Clica no botão "ver mais" até que não haja mais itens.

    Args:
        page: Página do Playwright
        url: URL da categoria
        secao: Seção (o-que-fazer, onde-comer, onde-ficar)
        categoria: Categoria específica

    Returns:
        Lista de dicts com dados de cada item
    """
    logger.info("[{}> {}] Iniciando extracao...".format(secao, categoria))

    try:
        # Navega para a URL
        await page.goto(url, wait_until="networkidle")
        logger.info("[{}> {}] Pagina carregada".format(secao, categoria))

        # Loop para clicar no botão "ver mais" até o final
        click_count = 0
        while True:
            # Aguarda um momento para garantir que o DOM está pronto
            await page.wait_for_timeout(500)

            # Procura pelo botão "ver mais"
            ver_mais_button = await page.query_selector('a:has-text("ver mais")')

            if not ver_mais_button:
                logger.info(
                    "[{}> {}] Nenhum botao 'ver mais' encontrado. Total de cliques: {}".format(secao, categoria, click_count)
                )
                break

            try:
                # Clica no botão "ver mais"
                await ver_mais_button.click()
                click_count += 1
                logger.info("[{}> {}] Clique {} em 'ver mais'".format(secao, categoria, click_count))

                # Aguarda novos itens carregarem
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(
                    "[{}> {}] Erro ao clicar no botao: {}".format(secao, categoria, e)
                )
                break

        # Obtém o HTML final da página
        html_content = await page.content()

        # Parse com BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Encontra todos os itens <li> na lista
        items = soup.find_all("li", class_="item")
        logger.info("[{}> {}] {} itens encontrados".format(secao, categoria, len(items)))

        # Extrai dados de cada item
        links = []
        for item in items:
            try:
                a_tag = item.find("a")
                if not a_tag:
                    continue

                url_item = a_tag.get("href")
                if not url_item:
                    continue

                # Tenta encontrar o h4 (nome)
                h4_tag = item.find("h4")
                nome = h4_tag.get_text(strip=True) if h4_tag else "Sem nome"

                # Tenta encontrar o p (subcategoria)
                p_tag = item.find("p")
                subcategoria = p_tag.get_text(strip=True) if p_tag else ""

                # Tenta encontrar a imagem
                img_tag = item.find("img")
                imagem_url = img_tag.get("src") if img_tag else ""

                link_data = {
                    "nome": nome,
                    "subcategoria": subcategoria,
                    "secao": secao,
                    "categoria": categoria,
                    "url": url_item,
                    "imagem_url": imagem_url,
                }

                links.append(link_data)
            except Exception as e:
                logger.warning("[{}> {}] Erro ao extrair item: {}".format(secao, categoria, e))
                continue

        logger.info("[{}> {}] [OK] {} links extraidos com sucesso".format(secao, categoria, len(links)))
        return links

    except Exception as e:
        logger.error("[{}> {}] [ERRO] Erro ao processar categoria: {}".format(secao, categoria, e))
        return []


async def extract_all_categories() -> List[Dict]:
    """
    Extrai links de todas as 18 categorias usando Playwright.

    Returns:
        Lista flat de todos os links de todas as categorias
    """
    all_links = []

    async with async_playwright() as p:
        # Lanca browser headless
        try:
            browser = await p.chromium.launch(headless=True)
        except PlaywrightError as e:
            mensagem = str(e)
            if "Executable doesn't exist" in mensagem or "playwright install" in mensagem:
                logger.error(BROWSER_MISSING_MSG)
                raise RuntimeError(BROWSER_MISSING_MSG) from e
            raise


        # User-Agent realista para evitar bloqueios
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # Itera sobre todas as secoes e categorias
            for secao, categorias in CATEGORY_URLS.items():
                logger.info("\n" + "="*60)
                logger.info("Processando secao: {}".format(secao))
                logger.info("="*60)

                for cat_data in categorias:
                    url = cat_data["url"]
                    categoria = cat_data["categoria"]

                    links = await extract_category_links(page, url, secao, categoria)
                    all_links.extend(links)

                    # Pequena pausa entre categorias para nao sobrecarregar o servidor
                    await page.wait_for_timeout(2000)

            logger.info("\n" + "="*60)
            logger.info("[OK] Extracao concluida!")
            logger.info("Total de links: {}".format(len(all_links)))
            logger.info("="*60 + "\n")

        finally:
            await context.close()
            await browser.close()

    return all_links


def extract_all_categories_sync() -> List[Dict]:
    """
    Wrapper síncrono para extract_all_categories (compatível com Dagster).
    """
    return asyncio.run(extract_all_categories())

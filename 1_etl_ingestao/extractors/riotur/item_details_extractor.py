"""
Extrator de Detalhes de Itens do RioTur
Extrai descricao, endereco, telefone, horario, email, website, redes sociais, tags
de cada pagina de detalhe no RioTur.Rio
"""

import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# Configuracao de logging: modulo de biblioteca nao configura o root logger.
# Quem executa decide (o Dagster faz isso via managed_python_loggers no dagster.yaml).
logger = logging.getLogger(__name__)

# Domínios de redes sociais para detecção
SOCIAL_DOMAINS = {
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "twitter.com": "Twitter",
    "x.com": "Twitter",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
    "linkedin.com": "LinkedIn",
    "whatsapp": "WhatsApp",
}

# Session com headers realistas
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


def is_social_media(url: str) -> bool:
    """Verifica se URL é de rede social"""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in SOCIAL_DOMAINS.keys())


def get_social_network_name(url: str) -> str:
    """Retorna o nome da rede social"""
    url_lower = url.lower()
    for domain, name in SOCIAL_DOMAINS.items():
        if domain in url_lower:
            return name
    return "Rede Social Desconhecida"


def clean_text(text: str) -> str:
    """Limpa texto removendo espaços extras"""
    if not text:
        return ""
    return " ".join(text.split())


def extract_emails(text: str) -> List[str]:
    """Extrai emails do texto"""
    if not text:
        return []
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))


def extract_phones(text: str) -> List[str]:
    """Extrai telefones do texto"""
    if not text:
        return []
    
    phones = []
    
    # Padrões de telefone brasileiro
    patterns = [
        r'\+55\s*\(?21\)?[\s.-]?\d{4,5}[\s.-]?\d{4}',  # +55 21 99999-9999
        r'\(\d{2}\)\s*\d{4,5}[\s.-]?\d{4}',            # (21) 9999-9999
        r'\d{2}\s*\d{4,5}[\s.-]?\d{4}',                # 21 9999-9999
        r'\+\d{1,3}\s*\d{2}\s*\d{4,5}[\s.-]?\d{4}',   # +55 21 99999-9999
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    
    # Remove duplicatas
    phones = list(set(phones))
    # Limpa espaços
    phones = [clean_text(p) for p in phones]
    
    return phones


def extract_description(soup: BeautifulSoup) -> str:
    """Extrai descricao principal do item"""
    try:
        # Procura por <p> tags no conteúdo principal
        # Geralmente vem logo depois do h1 ou h2
        
        # Tenta encontrar o container principal
        content = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
        
        if not content:
            content = soup
        
        # Encontra todos os paragrafos
        paragraphs = content.find_all("p")
        
        description = ""
        for p in paragraphs:
            text = clean_text(p.get_text())
            
            # Skip paragrafos que são apenas links ou muito curtos
            if len(text) > 20 and not text.startswith("http"):
                description += text + "\n"
            
            # Para em no maximo 3 paragrafos
            if description.count("\n") >= 3:
                break
        
        return clean_text(description)
    
    except Exception as e:
        logger.warning("Erro ao extrair descricao: {}".format(e))
        return ""


def extract_section_content(soup: BeautifulSoup, section_title: str, exclude_footer: bool = True) -> str:
    """Extrai conteudo de uma secao identificada por um titulo"""
    try:
        # Encontra o footer para poder excluir depois se necessário
        footer = soup.find("footer") if exclude_footer else None
        
        # Procura por <strong> que contem o titulo
        for strong in soup.find_all("strong"):
            # Verifica se está dentro do footer
            if footer and strong.find_parent("footer"):
                continue
            
            if section_title.lower() in strong.get_text().lower():
                # Pega o proximo elemento (geralmente <p>)
                next_elem = strong.find_next()
                if next_elem:
                    text = next_elem.get_text()
                    return clean_text(text)
        
        return ""
    
    except Exception as e:
        logger.warning("Erro ao extrair secao '{}': {}".format(section_title, e))
        return ""


def extract_content_serv(soup: BeautifulSoup, *termos_rotulo: str) -> str:
    """Le o conteudo de um bloco <div class="content-serv"> pelo seu rotulo.

    Cada campo da pagina (endereco, horario, e-mail, website) vive num bloco
    content-serv proprio, rotulado por um <strong>. Percorrer o documento a partir
    do <strong> (com find_next) atravessa a fronteira do bloco e engole os blocos
    seguintes - telefone, tags, horario -, que foi o que sujou a coleta de setembro.

    O separador no get_text e obrigatorio nos dois lados: sem ele os <br> colam
    palavras de linhas diferentes, tanto no conteudo ("GaveaRio de Janeiro") quanto
    no proprio rotulo ("horario deFuncionamento"), e ai a comparacao nunca casa.

    Args:
        soup: Pagina ja parseada
        termos_rotulo: Trechos aceitos no rotulo, em minusculas

    Returns:
        Conteudo do bloco sem o texto do rotulo, ou string vazia.
    """
    for bloco in soup.find_all("div", class_="content-serv"):
        if bloco.find_parent("footer"):
            continue

        rotulo = bloco.find("strong")
        if not rotulo:
            continue

        texto_rotulo = clean_text(rotulo.get_text(" ", strip=True))
        if not any(termo in texto_rotulo.lower() for termo in termos_rotulo):
            continue

        paragrafo = bloco.find("p")
        if paragrafo:
            return clean_text(paragrafo.get_text(" ", strip=True))

        # Sem <p>: usa o texto do bloco descontando o proprio rotulo
        texto = clean_text(bloco.get_text(" ", strip=True))
        if texto.lower().startswith(texto_rotulo.lower()):
            texto = texto[len(texto_rotulo):]
        return clean_text(texto)

    return ""


def extract_address(soup: BeautifulSoup) -> str:
    """Extrai endereco do bloco rotulado ENDERECO"""
    try:
        return extract_content_serv(soup, "endere")

    except Exception as e:
        logger.warning("Erro ao extrair endereco: {}".format(e))
        return ""


def extract_phone(soup: BeautifulSoup) -> List[str]:
    """Extrai telefone(s)"""
    try:
        # Procura por texto com padrão de telefone
        body_text = soup.get_text()
        phones = extract_phones(body_text)
        return phones
    
    except Exception as e:
        logger.warning("Erro ao extrair telefone: {}".format(e))
        return []


def extract_hours(soup: BeautifulSoup) -> str:
    """Extrai horario de funcionamento"""
    try:
        # Encontra o footer para poder excluir
        footer = soup.find("footer")
        
        # O horario tem bloco content-serv proprio; le direto dele, como o endereco.
        # O rotulo varia ("horario de Funcionamento", "Horarios"), por isso a busca
        # e por trecho e nao por titulo exato.
        hours = extract_content_serv(soup, "funcionamento", "horario", "horário")
        if hours:
            # O <p> da pagina costuma repetir o rotulo no inicio do valor
            # ("funcionamento das 11:30h ate 12:30h"); \b evita cortar "desde".
            hours = re.sub(
                r'^(?:(?:hor[áa]rio|de|funcionamento)\b|[:\-–\s])+',
                '', hours, flags=re.IGNORECASE,
            )
            return clean_text(hours).strip(" ,;.-")

        # Tenta extrair de secoes conhecidas
        for title_variant in ["horario de funcionamento", "horário de funcionamento",
                             "horarios", "horários", "funcionamento"]:
            hours = extract_section_content(soup, title_variant, exclude_footer=True)
            if hours:
                return hours
        
        # Se nao encontrou, procura por padrões de horário no texto
        # Procura padrões como "13h às 17h" ou "10:00-18:00"
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup
        text = main_content.get_text()
        
        # Remove footer do texto se possível
        if footer:
            footer_text = footer.get_text()
            text = text.replace(footer_text, "")
        
        # Padrões de horário
        time_patterns = [
            r'(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)[^,]*,?\s+das?\s+\d{1,2}[h:]\d{0,2}\s+às?\s+\d{1,2}[h:]\d{0,2}',
            r'\d{1,2}[h:]\d{0,2}\s+às?\s+\d{1,2}[h:]\d{0,2}',
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return clean_text(matches[0])
        
        return ""
    
    except Exception as e:
        logger.warning("Erro ao extrair horario: {}".format(e))
        return ""


def extract_email(soup: BeautifulSoup) -> str:
    """Extrai email"""
    try:
        # Encontra o footer para poder excluir
        footer = soup.find("footer")
        
        # Procura por links mailto (fora do footer)
        for a_tag in soup.find_all("a", href=True):
            # Skip se está no footer
            if footer and a_tag.find_parent("footer"):
                continue
            
            href = a_tag.get("href", "")
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0]
                return email
        
        # Se nao encontrou link, procura no texto (mas nao no footer)
        main_content = soup.find("main") or soup.find("article") or soup
        if footer:
            # Remove footer do conteúdo
            footer_copy = footer
        
        body_text = main_content.get_text() if main_content else ""
        emails = extract_emails(body_text)
        if emails:
            return emails[0]
        
        return ""
    
    except Exception as e:
        logger.warning("Erro ao extrair email: {}".format(e))
        return ""


def extract_website_and_socials(soup: BeautifulSoup) -> tuple:
    """Extrai website oficial e redes sociais"""
    website = None
    socials = []
    
    try:
        # Encontra o footer para poder excluir
        footer = soup.find("footer")
        
        # Procura por "website" label (fora do footer)
        for strong in soup.find_all("strong"):
            # Skip se está no footer
            if footer and strong.find_parent("footer"):
                continue
            
            if "website" in strong.get_text().lower():
                next_elem = strong.find_next("a")
                if next_elem and next_elem.get("href"):
                    url = next_elem.get("href")
                    
                    if is_social_media(url):
                        socials.append({
                            "rede": get_social_network_name(url),
                            "url": url
                        })
                    else:
                        website = url
        
        # Se nao encontrou website, procura todos os links (fora do footer, exceto mailto, #, etc)
        if not website:
            for a_tag in soup.find_all("a", href=True):
                # Skip se está no footer
                if footer and a_tag.find_parent("footer"):
                    continue
                
                href = a_tag.get("href", "")
                
                # Skip emails, anchors, vazios, etc
                if (href.startswith("http") and 
                    not href.startswith("mailto:") and
                    not href.startswith("javascript:") and
                    not "riotur.rio" in href and
                    not "facebook.com/share" in href and
                    not "twitter.com/share" in href and
                    not "whatsapp.com" in href and
                    not "carnaval.rio" in href and
                    not "reveillon.rio" in href):
                    
                    if is_social_media(href):
                        # Checa se ja existe
                        if not any(s["url"] == href for s in socials):
                            socials.append({
                                "rede": get_social_network_name(href),
                                "url": href
                            })
                    else:
                        # Primeira URL nao-social encontrada = website oficial
                        if not website:
                            website = href
        
        return website, socials
    
    except Exception as e:
        logger.warning("Erro ao extrair website/redes sociais: {}".format(e))
        return website, socials


def extract_tags(soup: BeautifulSoup) -> List[str]:
    """Extrai as tags do item (ex: "Gastronomia Asiatica", "Gavea").

    As tags sao links <a href=".../tag/..."> e o bloco que as contem **nao tem
    <strong>** de rotulo. A versao anterior procurava um <strong> com "tag" para se
    localizar, por isso devolvia lista vazia em todos os registros. Aqui os links
    sao encontrados direto pelo href, que e o unico marcador confiavel.
    """
    try:
        tags = []

        for link in soup.find_all("a", href=True):
            if "/tag/" not in link["href"]:
                continue
            if link.find_parent("footer"):
                continue

            tag_text = clean_text(link.get_text(" ", strip=True)).lstrip("#").strip()
            if tag_text and tag_text not in tags:
                tags.append(tag_text)

        return tags

    except Exception as e:
        logger.warning("Erro ao extrair tags: {}".format(e))
        return []


def extract_item_details(item_url: str, item_data: dict) -> dict:
    """
    Extrai detalhes completos de um item do RioTur
    
    Args:
        item_url: URL da página do item
        item_data: Dados básicos do item (nome, categoria, etc)
    
    Returns:
        Dict com todos os detalhes extraídos
    """
    logger.info("[{}] Extraindo detalhes...".format(item_data.get("nome", "Item")))
    
    try:
        # Faz request da página
        response = SESSION.get(item_url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extrai cada campo
        description = extract_description(soup)
        address = extract_address(soup)
        phones = extract_phone(soup)
        hours = extract_hours(soup)
        email = extract_email(soup)
        website, socials = extract_website_and_socials(soup)
        tags = extract_tags(soup)
        
        # Monta resultado
        result = {
            "nome": item_data.get("nome", ""),
            "descricao": description,
            "endereco": address,
            "telefones": phones,
            "horario": hours,
            "email": email,
            "website_oficial": website,
            "redes_sociais": socials,
            "tags": tags,
            "secao": item_data.get("secao", ""),
            "categoria": item_data.get("categoria", ""),
            "subcategoria": item_data.get("subcategoria", ""),
            "url_riotur": item_url,
            "imagem_url": item_data.get("imagem_url", ""),
            "data_extracao": datetime.now().isoformat()
        }
        
        logger.info("[{}] Detalhes extraidos com sucesso".format(item_data.get("nome")))
        return result
    
    except requests.exceptions.RequestException as e:
        logger.error("[{}] Erro de conexao: {}".format(item_data.get("nome"), e))
        return {
            "nome": item_data.get("nome", ""),
            "erro": "Falha ao conectar: {}".format(str(e)),
            "url_riotur": item_url,
            "data_extracao": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error("[{}] Erro ao extrair: {}".format(item_data.get("nome"), e))
        return {
            "nome": item_data.get("nome", ""),
            "erro": "Falha ao extrair: {}".format(str(e)),
            "url_riotur": item_url,
            "data_extracao": datetime.now().isoformat()
        }


def extract_all_items_details(items_links: List[dict]) -> List[dict]:
    """
    Extrai detalhes de todos os itens
    
    Args:
        items_links: Lista com dados basicos dos itens (do asset anterior)
    
    Returns:
        Lista com todos os detalhes extraídos
    """
    all_details = []
    total = len(items_links)
    
    logger.info("Iniciando extracao de detalhes de {} itens...".format(total))
    logger.info("=" * 70)
    
    for idx, item in enumerate(items_links, 1):
        try:
            details = extract_item_details(item["url"], item)
            all_details.append(details)
            
            # Progress
            if idx % 50 == 0:
                logger.info("[{}/{}] {} itens processados".format(idx, total, idx))
        
        except Exception as e:
            logger.warning("[{}/{}] Erro geral: {}".format(idx, total, e))
            all_details.append({
                "nome": item.get("nome", "?"),
                "erro": str(e),
                "url_riotur": item.get("url", ""),
                "data_extracao": datetime.now().isoformat()
            })
    
    logger.info("=" * 70)
    logger.info("[OK] Extracao completa! {} itens processados".format(total))
    
    return all_details

"""
Transformadores de Dados - RioTur
Converte JSON de detalhes em documentos de texto para embeddings
"""

import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Limpa texto removendo espaços extras e caracteres problemáticos"""
    if not text:
        return ""
    
    # Remove espaços multiplos
    text = " ".join(text.split())
    
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    
    return text.strip()


# Rodape institucional que o site cola no fim da descricao de ~200 itens, as vezes
# seguido da assinatura da prefeitura. Nao descreve o lugar e polui o vetor.
_RODAPE_RIOTUR = re.compile(
    r"Para entrar em contato conosco, envie um e-mail para \S+ ou preencha o "
    r"formul[aá]rio abaixo\..*$",
    re.DOTALL,
)


def clean_description(description: str) -> str:
    """Remove da descricao o rodape institucional do site e as marcas de nota (*).

    Os asteriscos sao chamadas de nota do site ("show* MPB", "musica ao vivo*")
    cuja nota nunca e extraida; sozinhos nao dizem nada e, no texto que o LLM le,
    podem ser confundidos com marcacao de markdown.
    """
    if not description:
        return ""

    description = _RODAPE_RIOTUR.sub("", description)
    description = description.replace("*", "")
    return clean_text(description)


def clean_address(address: str) -> str:
    """Limpa endereco removendo dados duplicados/sujos.

    Rede de seguranca: desde a correcao do extract_address (que agora le so o bloco
    content-serv do endereco, em vez de varrer o documento), o endereco ja chega
    limpo e estas substituicoes nao alteram nada numa amostra de 25 paginas. Fica
    como protecao para paginas com layout diferente do testado.
    """
    if not address:
        return ""

    # Remove patterns de telefone misturados
    address = re.sub(r'\+55\s*\(?21\)?.*?\d{4}', '', address)
    address = re.sub(r'\(\d{2}\)\s*\d{4,5}-?\d{4}', '', address)
    
    # Remove patterns de website/email misturados
    address = re.sub(r'https?://\S+', '', address)
    address = re.sub(r'www\.\S+', '', address)
    address = re.sub(r'\S+@\S+', '', address)
    
    # Remove "TAGS", "website", "E-mail" keywords se aparecerem
    address = re.sub(r'TAGS.*', '', address)
    address = re.sub(r'website.*', '', address)
    address = re.sub(r'E-mail.*', '', address)
    
    # Remove "ENDERECO" se estiver lá
    address = re.sub(r'ENDERECO', '', address)
    
    # Limpa espaços
    address = clean_text(address)
    
    return address


def clean_phone_list(phones: List[str]) -> List[str]:
    """Limpa lista de telefones removendo duplicatas"""
    if not phones:
        return []
    
    # Remove duplicatas
    cleaned = []
    seen = set()
    for phone in phones:
        phone = clean_text(phone)
        if phone and phone not in seen:
            cleaned.append(phone)
            seen.add(phone)
    
    return cleaned[:3]  # Máximo 3 telefones


def format_phone_list(phones: List[str]) -> str:
    """Formata lista de telefones para texto"""
    if not phones:
        return ""
    
    phones = clean_phone_list(phones)
    if len(phones) == 1:
        return phones[0]
    elif len(phones) == 2:
        return "{} ou {}".format(phones[0], phones[1])
    else:
        return ", ".join(phones[:-1]) + " ou " + phones[-1]


def extract_social_media_text(socials: List[Dict]) -> str:
    """Extrai texto de redes sociais"""
    if not socials:
        return ""
    
    social_names = []
    for social in socials[:2]:  # Máximo 2 redes sociais
        rede = social.get("rede", "").lower()
        if rede:
            social_names.append(rede.capitalize())
    
    if not social_names:
        return ""
    
    if len(social_names) == 1:
        return "{}".format(social_names[0])
    else:
        return " e ".join(social_names)


# O bairro aparece no endereco antes de "Rio de Janeiro"/"RJ"/CEP, apos um hifen.
_BAIRRO_NO_ENDERECO = re.compile(
    r'-\s*([^,\-\d]{2,40}?)\s*(?:Rio de Janeiro|-\s*RJ|\d{5})',
    re.IGNORECASE,
)


def extract_bairro(address: str) -> str:
    """Extrai o bairro do endereco.

    O bairro e muito buscado ("museus no Centro", "bares em Copacabana") e nao
    existe como campo proprio nos dados de origem.

    Args:
        address: Endereco ja limpo

    Returns:
        Nome do bairro, ou string vazia quando o padrao nao casa.
    """
    if not address:
        return ""

    match = _BAIRRO_NO_ENDERECO.search(address)
    return clean_text(match.group(1)) if match else ""


def build_document(item: Dict, tipo_padrao: str) -> str:
    """Monta o texto que sera convertido em vetor.

    Entra so o que serve para *encontrar* o lugar: nome, tipo, bairro, as tags do
    site (culinaria, tema) e a descricao. Endereco, telefone, e-mail, site e redes
    ficam de fora de proposito - eles ja estao no metadata, de onde o agente os le
    para exibir. Dentro do vetor um CEP ou um DDD nao ajudam a casar "comida
    asiatica" com nada, so ocupam a janela do modelo e diluem o sinal.

    Args:
        item: Detalhes brutos do item
        tipo_padrao: Descricao do tipo usada quando a subcategoria vem vazia

    Returns:
        Texto pronto para embedding.
    """
    nome = (item.get("nome") or "").strip()
    descricao = clean_description(item.get("descricao") or "")

    tipo = (item.get("subcategoria") or "").strip() or tipo_padrao
    bairro = extract_bairro(clean_address(item.get("endereco") or ""))

    cabecalho = "{}. {}".format(nome, tipo) if nome else tipo
    if bairro:
        cabecalho = "{}, {}".format(cabecalho, bairro)

    partes = [cabecalho.rstrip(".") + "."]

    # As tags do site trazem culinaria e tema ("Gastronomia Asiatica", "Museu"),
    # que e justamente o vocabulario das perguntas. O nome e descartado porque ja
    # abre o cabecalho.
    tags = [t for t in (item.get("tags") or []) if t and t.strip().lower() != nome.lower()]
    if tags:
        partes.append("{}.".format(", ".join(tags)))

    if descricao:
        partes.append(descricao)

    return clean_text(" ".join(partes))


def generate_document_o_que_fazer(item: Dict) -> str:
    """Gera documento de texto para categoria 'o-que-fazer'"""
    try:
        return build_document(item, "ponto turístico")

    except Exception as e:
        logger.warning("Erro ao gerar documento para '{}': {}".format(
            item.get("nome", "?"), e))
        return ""


def generate_document_onde_comer(item: Dict) -> str:
    """Gera documento de texto para categoria 'onde-comer'"""
    try:
        return build_document(item, "restaurante")
    
    except Exception as e:
        logger.warning("Erro ao gerar documento para '{}': {}".format(
            item.get("nome", "?"), e))
        return ""

def generate_document_onde_ficar(item: Dict) -> str:
    """Gera documento de texto para categoria 'onde-ficar'"""
    try:
        return build_document(item, "hospedagem")
    
    except Exception as e:
        logger.warning("Erro ao gerar documento para '{}': {}".format(
            item.get("nome", "?"), e))
        return ""

def generate_document(item: Dict) -> str:
    """
    Gera documento de texto a partir de um item JSON
    Seleciona template baseado na seçao
    """
    secao = item.get("secao", "").lower()
    
    if secao == "o-que-fazer":
        return generate_document_o_que_fazer(item)
    elif secao == "onde-comer":
        return generate_document_onde_comer(item)
    elif secao == "onde-ficar":
        return generate_document_onde_ficar(item)
    else:
        # Template padrão
        return generate_document_o_que_fazer(item)


def transform_items_to_documents(items: List[Dict]) -> List[Dict]:
    """
    Transforma lista de itens JSON em lista de documentos
    
    Cada documento tem:
    - id: identificador único
    - document: texto em linguagem natural
    - metadata: dados estruturados originais
    
    Args:
        items: Lista de dicts com detalhes dos itens
    
    Returns:
        Lista de dicts prontos para ChromaDB
    """
    documents = []
    ids_vistos = set()
    descartados_por_id = 0

    for idx, item in enumerate(items, 1):
        try:
            nome = item.get("nome", "item-{}".format(idx))
            
            # Gera documento de texto
            document_text = generate_document(item)
            
            if not document_text:
                logger.warning("[{}/{}] Documento vazio para '{}'".format(
                    idx, len(items), nome))
                continue
            
            endereco = clean_address(item.get("endereco") or "")

            # Cria metadados limpos
            metadata = {
                "nome": nome,
                "secao": item.get("secao", ""),
                "categoria": item.get("categoria", ""),
                "subcategoria": item.get("subcategoria", ""),
                # Bairro e tags viram campos proprios para permitir filtro no
                # ChromaDB (where={"bairro": "Copacabana"}), que a busca semantica
                # sozinha nao faz com precisao. Tags viram string porque o
                # ChromaDB so aceita escalares em metadata.
                "bairro": extract_bairro(endereco),
                "tags": ", ".join(item.get("tags") or []),
                "endereco": endereco,
                "telefone": format_phone_list(item.get("telefones") or []),
                "horario": clean_text(item.get("horario") or ""),
                "email": item.get("email", ""),
                "website": item.get("website_oficial", ""),
                "url_riotur": item.get("url_riotur", ""),
                "imagem_url": item.get("imagem_url", ""),
                "data_extracao": item.get("data_extracao", "")
            }

            # ChromaDB rejeita None em metadata ("Cannot convert Python object to
            # MetadataValue") e o extractor devolve None em campos opcionais como
            # website_oficial, onde o default do .get() nao se aplica.
            metadata = {k: ("" if v is None else v) for k, v in metadata.items()}

            # Cria ID único
            doc_id = "{}-{}".format(
                item.get("categoria", "unknown").replace(" ", "-").lower(),
                nome.replace(" ", "-").lower()[:30]
            )

            # O site lista o mesmo estabelecimento em URLs diferentes, gerando ids
            # repetidos. ChromaDB recusa o batch inteiro nesse caso, e documento
            # duplicado ainda polui a busca semantica.
            if doc_id in ids_vistos:
                descartados_por_id += 1
                logger.warning("[{}/{}] ID duplicado '{}' descartado ('{}')".format(
                    idx, len(items), doc_id, nome))
                continue
            ids_vistos.add(doc_id)

            documents.append({
                "id": doc_id,
                "document": document_text,
                "metadata": metadata
            })
            
            if idx % 100 == 0:
                logger.info("[{}/{}] {} documentos transformados".format(
                    idx, len(items), idx))
        
        except Exception as e:
            logger.error("Erro ao transformar item {}: {}".format(idx, e))
            continue
    
    if descartados_por_id:
        logger.warning("{} documentos descartados por ID duplicado".format(descartados_por_id))

    logger.info("[OK] {} documentos transformados com sucesso".format(len(documents)))
    return documents

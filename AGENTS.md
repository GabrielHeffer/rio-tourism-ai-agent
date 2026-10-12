# AGENTS.md — Instruções do Projeto

> **TCC — Rio Tourism AI Agent**
> Assistente de turismo do Rio de Janeiro com RAG, agentes LLM e pipeline ETL.

---

## 1. Identidade do Projeto

Monorepo com dois contextos delimitados (bounded contexts):

| Contexto | Responsabilidade | Tecnologia Principal |
|---|---|---|
| `1_etl_ingestao` | Extrair dados do RioTur, transformar e carregar em banco vetorial | Dagster + Playwright + ChromaDB |
| `2_agente_app` | Agente conversacional com RAG, ferramentas e orquestração | LangChain + LangGraph + OpenRouter |

**Fluxo de dados:** `RioTur.rio → Dagster ETL → ChromaDB → Agente LangGraph → Usuário`

---

## 2. Regra de Ouro — Código vs Comentários

```
┌─────────────────────────────────────────────────────────┐
│  CÓDIGO        → INGLÊS                                 │
│  (variáveis, funções, classes, módulos, tipos, enums)    │
│                                                          │
│  COMENTÁRIOS    → PORTUGUÊS (BR)                         │
│  (docstrings, inline comments, commit messages)          │
└─────────────────────────────────────────────────────────┘
```

```python
# ✅ Correto
def fetch_tourist_spots(category_urls: list[str]) -> list[dict]:
    """Busca os pontos turísticos a partir das URLs das categorias."""
    spots = []  # acumulador de pontos encontrados
    for url in category_urls:
        spots.extend(_scrape_category_page(url))
    return spots

# ❌ Errado — código em português
def buscar_pontos_turisticos(urls_das_categorias):
    # Fetches tourist spots from category URLs
    ...

# ❌ Errado — comentário em inglês
def fetch_tourist_spots(category_urls: list[str]) -> list[dict]:
    """Fetches tourist spots from category URLs."""  # ← deveria ser português
    ...
```

---

## 3. Convenções de Nomenclatura

> **VARIÁVEIS = SUBSTANTIVOS.** Nomeie pelo que a variável **é**.
> **FUNÇÕES = VERBOS.** Nomeie pelo que a função **faz**.

### 3.1 Variáveis — Substantivos Descritivos

Prefira nomes que respondam "o que é isso?" sem precisar ler o código ao redor.

```python
# ✅ Correto
tourist_spots     # substantivo claro, plural para coleção
category_url      # substantivo composto, específico
extracted_phones  # adjetivo + substantivo (de onde veio + o que é)
social_media_urls # domínio + substantivo
batch_size        # substantivo + medida

# ❌ Errado — genérico ou tipo no nome
data              # data do quê?
list              # lista de quê?
temp              # temporário por quê?
result            # resultado do quê?
phone_list        # não colocar tipo (list) no nome
```

### 3.2 Funções — Verbo + Objeto

Prefira nomes que respondam "o que essa função faz?" em uma frase curta.

```python
# ✅ Correto — verbo de ação + objeto claro
extract_address(soup)            # extrai endereço de um soup
clean_phone_list(phones)         # limpa lista de telefones
transform_items_to_documents()   # transforma itens em documentos
load_documents_to_chromadb()     # carrega documentos no ChromaDB
format_phone_list(phones)        # formata lista de telefones
is_social_media(url)             # pergunta: é rede social?

# ❌ Errado — verbo vago ou sem objeto
process()                        # processa o quê?
handle()                         # trata o quê?
do_stuff()                       # faz o quê?
get_data()                       # get só em getters de classe
address_data()                   # não é verbo, é substantivo
```

### 3.3 Hierarquia de Verbos por Módulo

| Módulo | Verbos Recomendados |
|---|---|
| Extractors | `fetch_`, `extract_`, `scrape_`, `collect_`, `gather_` |
| Transformers | `clean_`, `format_`, `normalize_`, `sanitize_`, `transform_`, `generate_`, `build_` |
| Loader | `load_`, `store_`, `persist_`, `save_`, `write_` |
| Queries | `find_`, `search_`, `query_`, `filter_`, `retrieve_` |
| Validação | `validate_`, `check_`, `verify_`, `ensure_`, `assert_` |

### 3.4 Regras de Escopo

```
Função curta (< 20 linhas)  → verbo específico:   extract_phones()
Função média (20-50 linhas) → verbo + objeto:      extract_item_details()
Função orquestradora (50+)  → verbo + contexto:    extract_all_items_details()
```

### 3.5 Nomes de Classe

Classes representam **entidades** (substantivos). Use `PascalCase`.

```python
# ✅ Correto
class RioTurExtractor     # entidade clara
class ChromaDBAdapter     # entidade + padrão (Adapter)
class TouristSpot         # modelo de domínio

# ❌ Errado
class ExtractData         # verbo — deveria ser função
class DatabaseConnector   # vago — qual banco? qual contexto?
```

### 3.6 Booleanos — Sempre Uma Pergunta

```python
# ✅ Correto
is_social_media(url)
has_website(item)
can_connect(db)
should_retry(attempt)

# ❌ Errado
check_social(url)     # não é pergunta
website_flag          # flag é descritivo, não booleano
```

---

## 4. Princípios de Clean Code

| Princípio | Aplicação no Projeto |
|---|---|
| **SRP** — Single Responsibility | Cada extractor tem uma única fonte de dados. `category_links_extractor.py` só extrai URLs. `item_details_extractor.py` só extrai detalhes. |
| **OCP** — Open/Closed | Novos parsers (ex: novo site oficial) são adicionados como novos arquivos, sem modificar os existentes. |
| **DRY** — Don't Repeat Yourself | `clean_text()`, `format_phone_list()`, `extract_section_content()` são compartilhadas entre todos os templates. |
| **KISS** — Keep It Simple | Funções puras com type hints. Sem herança profunda. Sem metaclasses. |
| **Fail Fast** | Validação no topo da função. Se entrada é inválida, `return ""` ou `raise` imediatamente. Não propaga `None`. |
| **Composition over Inheritance** | Composição de funções (`generate_document()` chama helpers). Nunca herança de 3+ níveis. |
| **Explicit over Implicit** | Type hints em toda função pública. Nomes autoexplicativos. Sem `*args`/`**kwargs` sem documentar. |
| **LoD** — Law of Demeter | Máximo 1 nível de profundidade: `item.get("nome")` ✅ — `item["metadata"]["address"]["street"]` ❌ |

---

## 5. Padrões de Arquitetura

### 5.1 Macro — Visão Geral

```
┌──────────────────────────────────────────────────────────────┐
│                       MONOREPO                                │
│                                                               │
│  ┌────────────────────────┐   ┌───────────────────────────┐  │
│  │   1_etl_ingestao       │   │   2_agente_app             │  │
│  │   (Bounded Context 1)  │   │   (Bounded Context 2)      │  │
│  │                        │   │                            │  │
│  │  Pipeline Pattern      │   │  Hexagonal Architecture    │  │
│  │  Extract → Transform   │───→  Ports & Adapters          │  │
│  │  → Load → ChromaDB     │   │  LangGraph State Machine   │  │
│  │                        │   │  Tool-using Agent          │  │
│  └────────────────────────┘   └───────────────────────────┘  │
│                                                               │
│  Camadas de dados: RAW → INTERMEDIATE → WAREHOUSE → SERVE    │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Pipeline Pattern — ETL com Dagster

Cada asset do Dagster representa um **estágio do pipeline**. A dependência entre assets forma um DAG (grafo acíclico dirigido).

```
riotur_category_links ──→ riotur_item_details ──→ riotur_documents ──→ chromadb_turismo_rio
       (raw)                  (raw)                 (intermediate)          (warehouse)
```

- **Asset = artefato de dado**, não tarefa
- Cada asset pode ser rematerializado independentemente
- Tags `layer` indicam a fase: `raw`, `intermediate`, `warehouse`

### 5.3 Hexagonal Architecture — Agente App

```
┌───────────────────────────────────────────────┐
│                 DOMAIN                         │
│  Entidades puras de negócio                    │
│  (TouristSpot, SearchResult, Conversation)     │
├───────────────────────────────────────────────┤
│                 PORTS                          │
│  Interfaces abstratas (contratos)              │
│  (VectorStorePort ✅, LLMPort ✅, WeatherPort)   │
├───────────────────────────────────────────────┤
│                 ADAPTERS                       │
│  Implementações concretas                      │
│  (ChromaDBAdapter ✅, OpenRouterAdapter ✅, ...) │
├───────────────────────────────────────────────┤
│                 GRAPH                          │
│  Orquestração com LangGraph                    │
│  (nós, arestas, estado, ferramentas)           │
│  ✅ tools/rag_tool.py — search_tourist_spots    │
│  ✅ state.py, prompts.py, agent_graph.py        │
└───────────────────────────────────────────────┘
        ▲
        │ (composition root — conecta adapters concretos aos ports)
   ✅ composition.py  ←── ✅ main.py (handle_message)
```

**Regra de dependência:** Domain não importa nada externo. Ports são interfaces. Adapters implementam ports. Graph orquestra via ports. `graph/tools/rag_tool.py` e `graph/agent_graph.py` importam só `ports/` e `domain/` — nunca `adapters/` nem `shared/` diretamente; as implementações concretas são injetadas de fora, em `composition.py`.

`LLMPort` (`ports/llm_port.py`) fala o vocabulário do LangChain (`BaseMessage`, `AIMessage`, `BaseTool`) em vez de um tipo de domínio próprio — decisão deliberada, já que `graph/` é 100% comprometido com LangGraph e não há benefício em esconder esses tipos atrás de outro wrapper. O que a porta isola é **o provedor/modelo** por trás (`OpenRouterAdapter`, em `adapters/openrouter_adapter.py`, usa `langchain_openai.ChatOpenAI` apontado pro endpoint OpenAI-compatible do OpenRouter — modelo e API key configuráveis via `OPENROUTER_MODEL`/`OPENROUTER_API_KEY`).

**`composition.py` é o composition root de verdade** (não `main.py`): conecta `OpenRouterAdapter`+`ChromaDBAdapter` às ports e monta o grafo via `get_agent_graph()` (construção preguiçosa e cacheada — `OpenRouterAdapter()` levanta erro na hora se `OPENROUTER_API_KEY` não estiver setada, então nada é construído até a primeira mensagem chegar). `main.py` é só **um** dos pontos de entrada possíveis (`handle_message(user_message, thread_id)`) — uma API HTTP futura importaria `composition.get_agent_graph()` do mesmo jeito, sem depender de `main.py`.

O loop do agente (`graph/agent_graph.py`) é o `StateGraph` clássico de tool-calling: nó `agent` chama `LLMPort.generate_response(messages, tools)`; `tools_condition` (utilitário do LangGraph) olha se a resposta tem `tool_calls` — se sim, roteia pro nó `tools` (`ToolNode`, executa a tool e devolve `ToolMessage`) e volta pro `agent`; se não, vai pro `END` com a resposta final. Repete até o LLM responder sem pedir tool.

**Memória de curto prazo (histórico da conversa):** o grafo é compilado com um *checkpointer* do LangGraph, que salva o `AgentState` ao fim de cada execução e o recarrega na próxima chamada com o mesmo `thread_id` (`config={"configurable": {"thread_id": ...}}`). Por isso `handle_message(user_message, thread_id)` envia **só a mensagem nova**. Três regras:
- **Checkpointer injetado:** `build_agent_graph(llm, tools, system_prompt, checkpointer=None)` não sabe onde o histórico vive. O `composition.py` cria um `SqliteSaver` (pacote `langgraph-checkpoint-sqlite`) no arquivo de `AGENT_MEMORY_PATH`, com `check_same_thread=False`, porque o `ToolNode` roda tools em threads. Nos testes do grafo, use `InMemorySaver`.
- **Prompt de sistema fora do estado:** o nó `agent` coloca o `SystemMessage` na frente das mensagens só na hora de chamar o LLM. Ele nunca é gravado no histórico; assim não se repete, e trocar o prompt vale também para conversas antigas.
- **Janela:** o LLM recebe só as últimas `MAX_HISTORY_MESSAGES` (20) mensagens, via `select_recent_messages` (`trim_messages` com `start_on="human"`, para nunca começar num resultado de tool órfão). O histórico completo continua salvo.

`composition.delete_conversation(thread_id)` apaga uma conversa (dados pessoais / LGPD). Isto **não** é memória de longo prazo: não há fatos por usuário entre conversas.

**Implementado:** `domain/tourist_spot.py`, `domain/search_result.py`, `ports/vector_store_port.py`, `adapters/chromadb_adapter.py`, `ports/llm_port.py`, `adapters/openrouter_adapter.py`, `graph/tools/rag_tool.py`, `graph/state.py`, `graph/prompts.py`, `graph/agent_graph.py`, `composition.py`, `main.py`, memória de curto prazo (checkpointer SQLite). Pendente: memória de longo prazo (fatos por usuário, `Store` do LangGraph), outras tools (clima, Google Places, busca na internet) e uma API HTTP para expor o agente (hoje só o chat local do `main.py`).

### 5.4 Padrão de Camadas (ETL)

| Camada | Tag Dagster | Descrição |
|---|---|---|
| **Raw** | `layer: raw` | Dados brutos extraídos da fonte (sem transformação) |
| **Intermediate** | `layer: intermediate` | Dados limpos e transformados, prontos para consumo |
| **Warehouse** | `layer: warehouse` | Dados persistidos em banco vetorial, indexados |

---

## 6. Design Patterns em Uso

| Pattern | Onde | Por quê |
|---|---|---|
| **Strategy** | `item_details_extractor.py` | Cada campo tem sua própria estratégia de parsing (regex para telefone, seção `strong` para endereço, etc.) |
| **Template Method** | `document_transformer.py` — `generate_document_*()` | Estrutura comum (nome + descrição + infos) com variação por seção |
| **Adapter** | `shared/vector_store.py` — `ChromaVectorStore` | Isola a dependência externa (ChromaDB + embedding model). Trocar por Weaviate/Pinecone requer só essa classe. `loader.py` é uma Facade fina sobre ela — ver seção 7.1. |
| **Multi-tenant Collection** | `ChromaVectorStore.load_documents(documents, source=..., replace_existing=...)` | Uma única collection `riotur-turismo` compartilhada por múltiplas fontes. Cada documento é tagueado com `metadata["fonte"]`. `replace_existing=True` (padrão) substitui só os documentos da `source` informada (`collection.delete(where={"fonte": source})`) antes de inserir, preservando dados de outras fontes; `replace_existing=False` só faz append (sem apagar nada). |
| **Facade** | `category_links_extractor.py` — `extract_all_categories_sync()` | Interface simples que esconde a complexidade do Playwright assíncrono |
| **Factory** | `document_transformer.py` — `generate_document()` | Seleciona o template correto baseado na seção do item |
| **Dependency Injection** | Assets Dagster; `graph/tools/rag_tool.py` — `build_search_tourist_spots_tool(vector_store)`; `graph/agent_graph.py` — `build_agent_graph(llm, tools)` | Cada asset recebe os dados do asset anterior via parâmetro da função (sem acoplamento). A tool de RAG e o grafo do agente recebem a `VectorStorePort`/`LLMPort` já construídas — `graph/` nunca instancia `ChromaDBAdapter`/`OpenRouterAdapter` diretamente. |
| **Composition Root** | `2_agente_app/composition.py` — `get_agent_graph()` | Único lugar que conhece as implementações concretas (`OpenRouterAdapter`, `ChromaDBAdapter`) e as injeta nos factories de `graph/`. Construção preguiçosa e cacheada (`OpenRouterAdapter()` falha na hora se faltar `OPENROUTER_API_KEY`). `main.py` (e uma futura API) só importam `get_agent_graph()` daqui — nunca instanciam adapter nenhum sozinhos. |
| **Chain of Responsibility** | `item_details_extractor.py` — `extract_hours()` | Tenta múltiplas estratégias em sequência até encontrar o dado |

---

## 7. Estrutura de Pastas

```
rio-tourism-ai-agent/
│
├── shared/                             ← Recursos compartilhados entre os dois contextos
│   ├── vector_store.py                ← ChromaVectorStore: conexão, embeddings, insert/query/stats
│   └── tests/
│       └── test_vector_store.py
│
├── 1_etl_ingestao/                    ← Pipeline ETL (Bounded Context 1)
│   ├── run_etl.py                     ← Definições de assets + entry point Dagster
│   ├── document_transformer.py        ← JSON → texto corrido + limpeza de dados
│   ├── loader.py                      ← Facade fina sobre shared/vector_store.py
│   ├── extractors.py                  ← [stub legado — não modificar]
│   ├── extractors/                    ← Módulo de extractors modulares
│   │   └── riotur/                    ← Extractors específicos do RioTur.Rio
│   │       ├── category_links_extractor.py   ← Playwright: 18 categorias, 407 URLs
│   │       └── item_details_extractor.py     ← Requests+BS4: detalhes de cada URL
│   ├── tests/                         ← Testes pytest (scripts soltos de teste não ficam aqui fora)
│   └── __init__.py
│
├── 2_agente_app/                      ← Agente IA (Bounded Context 2)
│   ├── main.py                        ← Chat no terminal (--thread <id> retoma): handle_message(user_message, thread_id)
│   ├── composition.py                 ← Composition root: get_agent_graph() conecta adapters e checkpointer SQLite aos ports
│   ├── domain/
│   │   ├── tourist_spot.py            ← Entidade: ponto turístico/restaurante/hospedagem
│   │   └── search_result.py           ← Entidade: resultado de busca semântica
│   ├── ports/
│   │   ├── vector_store_port.py       ← VectorStorePort: contrato de busca semântica
│   │   └── llm_port.py                ← LLMPort: contrato de geração de resposta (+ tool-calling)
│   ├── adapters/
│   │   ├── chromadb_adapter.py        ← ChromaDBAdapter: implementa VectorStorePort via shared/vector_store.py
│   │   └── openrouter_adapter.py      ← OpenRouterAdapter: implementa LLMPort via langchain_openai.ChatOpenAI
│   └── graph/
│       ├── state.py                   ← AgentState: historico de mensagens (TypedDict + add_messages)
│       ├── prompts.py                 ← TOURISM_AGENT_SYSTEM_PROMPT: persona/tom/idioma
│       ├── agent_graph.py             ← build_agent_graph: StateGraph do loop agent→tools→agent (+ checkpointer e janela)
│       └── tools/                     ← Uma tool por arquivo (SRP)
│           └── rag_tool.py            ← build_search_tourist_spots_tool: tool de RAG (StructuredTool)
│           # weather_tool.py, google_places_tool.py [pendentes]
│
├── data_raw/                          ← Saídas do ETL (fora do Git; regeneradas pelo Dagster)
│   ├── riotur_links.json              ← Asset 1: links de categorias (~1064 na extração de 29/09/2026)
│   ├── riotur_details.json            ← Asset 2: detalhes de cada item
│   └── riotur_documents.json          ← Asset 3: documentos prontos p/ embedding
│
├── chroma_db_rio/                     ← Persistência do ChromaDB (não versionar conteúdo)
│
├── .env.example                       ← Template de variáveis de ambiente
├── requirements.txt                   ← Dependências Python
├── README.md                          ← Documentação geral do projeto
└── AGENTS.md                          ← Este arquivo
```

### 7.1 Por que `shared/`?

RAG exige que documentos indexados e perguntas do usuário sejam embutidos
pelo **mesmo modelo de embeddings** — caso contrário a busca por similaridade
não funciona. Por isso a conexão com o ChromaDB e o modelo de embeddings
(`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) vivem numa
classe única, `ChromaVectorStore` em `shared/vector_store.py`, usada tanto
pelo ETL quanto (futuramente) pelo agente:

```
shared/vector_store.py — ChromaVectorStore
    ├── load_documents(documents, source, replace_existing)  ← escrita
    ├── search_documents(query_text, n_results)               ← leitura
    └── get_stats()                                           ← leitura

1_etl_ingestao/loader.py  → instancia ChromaVectorStore, expõe funções (Facade)
2_agente_app/adapters/chromadb_adapter.py → ChromaDBAdapter instancia ChromaVectorStore
```

**Import entre pastas com dígito:** `1_etl_ingestao` e `2_agente_app` começam
com número, então não são nomes válidos de pacote Python
(`import 1_etl_ingestao` é `SyntaxError`). O projeto contorna isso inserindo a
raiz do repo em `sys.path` manualmente (`sys.path.insert(0, ...)`) em
`loader.py`, em `adapters/chromadb_adapter.py` (ambos precisam alcançar
`shared`) e em cada `conftest.py` de teste. `pytest.ini` usa
`--import-mode=importlib` e nenhum `tests/__init__.py` existe dentro de
`1_etl_ingestao/tests` ou `2_agente_app/tests`, para evitar colisão de nome de
módulo entre os dois diretórios `tests/` (ambos ficariam com o mesmo nome
"tests" já que a pasta pai com dígito não pode entrar no caminho do módulo).

Dentro do próprio `2_agente_app`, os módulos `domain`, `ports`, `adapters` e
`graph` se importam entre si com nomes flat (`from ports.x import Y`), o que
exige `2_agente_app/` (não só a raiz do repo) no `sys.path`. Três pontos
fazem esse insert: `adapters/chromadb_adapter.py` (que também precisa da raiz
do repo, pra chegar em `shared`), `composition.py` (o composition root — é
ele quem de fato cruza pra `adapters`/`graph` a partir de qualquer entry
point, `main.py` hoje ou uma API no futuro) e `2_agente_app/tests/conftest.py`
— os demais arquivos (`ports/vector_store_port.py`, `graph/tools/rag_tool.py`,
`graph/agent_graph.py`, `main.py`) não precisam de `sys.path` próprio porque,
na prática, só são importados depois que um desses três pontos já rodou.

---

## 8. Convenções Gerais

### 8.1 Imports

```python
# 1. stdlib
import logging
from pathlib import Path
from typing import List, Dict

# 2. third-party
import dagster as dg
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# 3. project
from extractors.riotur.category_links_extractor import extract_all_categories_sync
from document_transformer import transform_items_to_documents
```

### 8.2 Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use .format() — compatível com Windows (sem f-strings em logs)
logger.info("[{}] Extraindo detalhes...".format(nome))

# Níveis de log
logger.debug("debug detalhado")   # só em desenvolvimento
logger.info("info operacional")    # progresso, marcos
logger.warning("alerta não fatal") # falha recuperável
logger.error("erro que exige atenção") # falha que interrompe fluxo
```

### 8.3 Error Handling

```python
# Em extractors (scraping) — NUNCA deixar um item quebrar o lote
try:
    data = extract_item(url)
except Exception as e:
    logger.warning("Falha ao extrair {}: {}".format(url, e))
    continue  # próximo item

# Em assets Dagster — falhar rápido e com contexto
try:
    assets = process_all()
except Exception as e:
    context.log.error("[ERRO] Falha ao processar: {}".format(e))
    raise  # Dagster marca asset como failed
```

### 8.4 Type Hints

Obrigatórios em toda função pública. `typing` para versões < 3.12.

```python
# ✅ Correto
def extract_item_details(url: str, data: dict) -> dict:
    """Extrai os detalhes completos de um item."""

# ❌ Errado
def extract_item_details(url, data):
    # sem type hints
```

### 8.5 Encoding

```python
# Sempre UTF-8 ao ler/escrever arquivos
with open("arquivo.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 9. Anti-Padrões (NÃO FAZER)

| Anti-Padrão | Exemplo | Correção |
|---|---|---|
| **Engolir exceções** | `except: pass` | `except Exception as e: logger.warning(...)` |
| **Print em produção** | `print(dados)` | `logger.info(...)` |
| **Função gigante** | 100+ linhas | Extrair helpers de no máximo 30 linhas |
| **Magic numbers** | `time.sleep(3.5)` | `DELAY_BETWEEN_REQUESTS = 3.5` |
| **Comentário óbvio** | `# incrementa i` em `i += 1` | Remover o comentário |
| **Stateful globals** | Mutar variável de módulo | Passar como parâmetro ou retornar valor |
| **Stringly typed** | `if tipo == "museu":` | Usar enum ou constante |
| **Deep nesting** | 4+ níveis de `if`/`for` | Early return, extrair função |
| **Mutable default** | `def f(x=[]):` | `def f(x=None):` + inicializar dentro |
| **F-strings em logs** | `logger.info(f"{x}")` | `logger.info("{}".format(x))` — compatível Windows |
| **Nome de módulo colidindo com pacote PyPI** | Um arquivo do projeto chamado `transformers.py` | Nunca nomear um módulo local igual a um pacote de terceiros usado no projeto (ex: `transformers`, `requests`, `types`). `1_etl_ingestao/tests/conftest.py` insere `1_etl_ingestao/` no início do `sys.path` — um `transformers.py` local ali escondia o pacote real `transformers` (dependência do `sentence-transformers`/ChromaDB) pro resto do processo, quebrando o carregamento do modelo de embeddings de forma silenciosa e só nos testes que rodavam depois. Por isso o antigo `transformers.py` do ETL foi renomeado pra `document_transformer.py`. |

---

## 10. Dagster Asset Graph

```
┌──────────────────────────┐
│  riotur_category_links   │  ← Asset 1 — Playwright
│  tags: {layer: raw}      │     Scraping 18 categorias
│  output: 407 URLs        │     Clica "ver mais" até o fim
└────────────┬─────────────┘
             │ depende de
             ↓
┌──────────────────────────┐
│  riotur_item_details     │  ← Asset 2 — Requests + BS4
│  tags: {layer: raw}      │     Para cada URL, extrai:
│  output: 407 itens       │     descrição, endereço, tel,
│                          │     horário, email, website
└────────────┬─────────────┘
             │ depende de
             ↓
┌──────────────────────────┐
│  riotur_documents        │  ← Asset 3 — Transformação
│  tags: {layer: intermed} │     JSON → texto corrido
│  output: 214 docs        │     Templates por seção
│                          │     Limpeza de dados sujos
└────────────┬─────────────┘
             │ depende de
             ↓
┌──────────────────────────┐
│  chromadb_turismo_rio    │  ← Asset 4 — Load
│  tags: {layer: warehouse}│     Gera embeddings
│  output: Vector Store    │     Carrega ChromaDB
└──────────────────────────┘
```

### Como Materializar

```bash
# Web UI (recomendado)
cd 1_etl_ingestao
dagster dev -f run_etl.py
# Acessar http://localhost:3000 → clicar "Materialize all"

# Ou via linha de comando (sem UI)
cd 1_etl_ingestao
dagster asset materialize -f run_etl.py --select "*"
```

Nunca rode o agente enquanto `chromadb_turismo_rio` estiver carregando: dois processos no mesmo `PersistentClient` corromperam o índice HNSW uma vez.

---

## 11. Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `OPENROUTER_API_KEY` | Chave do provedor LLM (OpenRouter) | Sim |
| `OPENROUTER_MODEL` | Modelo usado no OpenRouter (padrão: `deepseek/deepseek-v4-flash-0731`) | Não |
| `OPENWEATHER_API_KEY` | API de clima em tempo real | Não |
| `GOOGLE_PLACES_API_KEY` | API de locais do Google | Não |
| `CHROMA_DB_PATH` | Caminho do banco vetorial (relativo é ancorado na raiz do repo). **Fora de pastas sincronizadas** (OneDrive etc.) — a sincronização corrompe o índice HNSW (`Error loading hnsw index`); nesse caso use caminho absoluto | Sim (padrão: `./chroma_db_rio`) |
| `AGENT_MEMORY_PATH` | Arquivo SQLite da memória de conversa do agente (relativo é ancorado na raiz do repo). Mesma regra do `CHROMA_DB_PATH`: **fora de pastas sincronizadas**. Contém dados pessoais: fica fora do Git (`*.sqlite`) | Não (padrão: `./agent_memory.sqlite`) |
| `ENVIRONMENT` | `development` ou `production` | Sim |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Sim (padrão: `INFO`) |

---

## 13. Regras de Teste

### 13.1 Regra de Ouro para Mudanças

```
┌─────────────────────────────────────────────────────────────┐
│  PARA TODA MUDANÇA DE CÓDIGO:                               │
│                                                              │
│  1. Avalie se alguma regra de negócio foi alterada          │
│  2. Se sim → ATUALIZE os testes ANTES ou JUNTO do código    │
│  3. Se não → apenas rode os testes existentes               │
│  4. Rode `pytest` antes de cada commit                      │
│  5. Só faça commit se TODOS os testes passarem              │
└─────────────────────────────────────────────────────────────┘
```

### 13.2 O Que é "Regra de Negócio"?

Mudanças que **alteram o comportamento observável** do sistema — ou seja, o que entra e o que sai — devem ter testes atualizados.

| Mudança | É regra de negócio? | Ação |
|---|---|---|
| Alterar template de documento (`generate_document_*`) | Sim | Atualizar `test_document_transformer.py` |
| Novo campo extraído do HTML | Sim | Adicionar teste em `test_item_details_extractor.py` |
| Mudar regex de telefone/email | Sim | Atualizar teste correspondente |
| Alterar lógica de limpeza (`clean_address`) | Sim | Atualizar `test_document_transformer.py` |
| Novo asset Dagster | Sim | Adicionar teste em `test_assets.py` |
| Corrigir typo em log | Não | Só rodar testes |
| Refatorar nome de variável interna | Não | Só rodar testes |
| Alterar timeout/delay | Não | Só rodar testes |

### 13.3 Estrutura de Testes

```
1_etl_ingestao/
└── tests/
    ├── __init__.py
    ├── conftest.py                              ← fixtures compartilhadas
    ├── fixtures/                                 ← HTMLs reais p/ mock
    │   ├── categoria_cultura_arte.html
    │   ├── detalhe_museu_naval.html
    │   ├── detalhe_ago.html
    │   └── detalhe_copacabana_palace.html
    ├── test_category_links_extractor.py          ← 14 testes (estrutura de URLs + parsing)
    ├── test_item_details_extractor.py            ← 27 testes (parsers de cada campo)
    ├── test_document_transformer.py                      ← 37 testes (limpeza + templates)
    ├── test_loader.py                            ← 9 testes (ChromaDB mockado)
    └── test_assets.py                            ← 12 testes (integração Dagster + JSON)

2_agente_app/
└── tests/                                        ← (reservado para o agente)
    ├── __init__.py
    ├── conftest.py
    ├── test_domain/
    ├── test_ports/
    ├── test_adapters/
    └── test_graph/
```

### 13.4 Convenções de Teste

| Regra | Exemplo |
|---|---|
| **Arquivo** | `test_<nome_do_modulo>.py` |
| **Classe** | `class Test<NomeDaFuncionalidade>` — agrupa testes relacionados |
| **Função** | `test_<o_que_esta_sendo_testado>()` — descritivo em português |
| **Fixture HTML** | Salvar HTML real em `tests/fixtures/`, nunca inventar mock |
| **Fixture Python** | Definir em `conftest.py` com dados que simulam saída real dos assets |
| **Mock** | Só para dependências externas (HTTP, ChromaDB, Playwright) |
| **Skip** | Usar `pytest.mark.skipif` para dependências opcionais (ex: chromadb) |
| **Markers** | `@pytest.mark.integration` (requer arquivos JSON), `@pytest.mark.slow` (+5s) |
| **Assert** | Um conceito por teste. Mensagem clara se falhar |

### 13.5 Exemplo de Teste Bem Escrito

```python
class TestExtractAddress:
    """Testes para extracao de endereco"""

    def test_extract_address_museu_naval(self, museu_naval_html):
        """Endereco do Museu Naval contem 'Rua Dom Manuel'"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        address = extract_address(soup)
        assert "Rua Dom Manuel" in address or "Dom Manuel" in address

    def test_extract_address_returns_string(self, museu_naval_html):
        """Endereco sempre retorna string, nunca None"""
        soup = BeautifulSoup(museu_naval_html, "html.parser")
        address = extract_address(soup)
        assert isinstance(address, str)
```

### 13.6 Comandos

```bash
# Rodar todos os testes
pytest

# Rodar testes de um módulo específico
pytest 1_etl_ingestao/tests/test_document_transformer.py -v

# Rodar com coverage
pytest --cov=1_etl_ingestao --cov-report=term-missing

# Rodar apenas testes unitários (pular integração)
pytest -m "not integration"

# Rodar antes de cada commit
pytest && git commit ...
```

### 13.7 CI Mental (antes de cada commit)

```
┌─────────────────────────────────────────────┐
│  1. git diff → avaliar o que mudou          │
│  2. Mudou lógica de negócio?                │
│     SIM → atualizar/adicionar testes        │
│     NÃO → pular para 3                      │
│  3. pytest → todos passam?                  │
│     SIM → commit                            │
│     NÃO → corrigir código ou teste          │
└─────────────────────────────────────────────┘
```

---

**Última atualização:** Agosto 2026
**Manter atualizado:** Sim — modificar sempre que a estrutura de pastas, convenções ou assets mudarem.
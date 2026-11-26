# Rio Tourism AI Agent

> Assistente de turismo do Rio de Janeiro com RAG, agentes LLM e pipeline ETL automatizado.

---

## Visão Geral

Agente IA que responde perguntas sobre turismo no Rio de Janeiro usando:

- **RAG (Retrieval Augmented Generation):** Recuperação semântica de informações turísticas
- **Agentes LLM:** Orquestração via LangGraph com ferramentas (clima, busca, etc.)
- **Banco Vetorial:** ChromaDB com embeddings multilíngues
- **Pipeline ETL:** Dagster orquestrando extração, transformação e carga

---

## Arquitetura

```
┌──────────────┐    ┌────────────────────┐    ┌────────────────┐
│   RioTur.rio │───→│  Dagster ETL       │───→│  ChromaDB      │
│   (18 cats)  │    │  (4 assets)        │    │  (embeddings)  │
└──────────────┘    └────────────────────┘    └────────────────┘
                           │                          │
                           ↓                          ↓
                      data_raw/                   chroma_db_rio/
                    riotur_*.json
                                                        │
                                           ┌────────────┴────────────┐
                                           │   Agente LangGraph      │
                                           │   (Hexagonal Arch)      │
                                           └────────────────────────┘
                                                     │
                                                     ↓
                                                Resposta RAG
```

### Padrões de Arquitetura

| Camada | Padrão | Motivo |
|---|---|---|
| **ETL** | Pipeline Pattern (Dagster) | Cada asset é um artefato de dado independente e rematerializável |
| **Agente** | Hexagonal (Ports & Adapters) | Domain isolado, adapters trocáveis, testabilidade |
| **Orquestração** | LangGraph State Machine | Controle de fluxo do agente com nós, arestas e estado tipado |
| **Dados** | Camadas (Raw → Intermediate → Warehouse) | Separação clara entre dados brutos, transformados e persistidos |

---

## Stack Tecnológico

| Componente | Tecnologia | Uso |
|---|---|---|
| **Orquestração ETL** | Dagster 1.13 | Definição e execução de assets |
| **Web Scraping (dinâmico)** | Playwright 1.50 | Headless Chromium para páginas com "ver mais" |
| **Web Scraping (estático)** | BeautifulSoup4 4.12 + Requests 2.32 | Parsing HTML de páginas de detalhe |
| **Banco Vetorial** | ChromaDB 1.5 | Persistência e busca semântica |
| **Embeddings** | Sentence Transformers 5.x | `paraphrase-multilingual-MiniLM-L12-v2` |
| **LLM Framework** | LangChain 1.3 + LangGraph | Agente conversacional com ferramentas |
| **LLM Provider** | OpenRouter | Acesso a modelos Claude, GPT, etc. |
| **Runtime** | Python 3.10+ | — |

---

## Pipeline ETL

```
┌─────────────────────────────┐
│  Asset 1: riotur_category_links     │  Playwright
│  layer: raw                         │  18 categorias
│  output: 407 URLs                   │  Clica "ver mais"
└──────────────┬──────────────────┘
               ↓
┌─────────────────────────────┐
│  Asset 2: riotur_item_details       │  Requests + BS4
│  layer: raw                         │  Descrição, endereço,
│  output: 407 itens                  │  telefone, horário,
│                                     │  email, website, redes
└──────────────┬──────────────────┘
               ↓
┌─────────────────────────────┐
│  Asset 3: riotur_documents          │  Transformação
│  layer: intermediate                │  JSON → texto corrido
│  output: 214 docs                   │  Templates por seção
│                                     │  Limpeza de dados
└──────────────┬──────────────────┘
               ↓
┌─────────────────────────────┐
│  Asset 4: chromadb_turismo_rio      │  Load
│  layer: warehouse                   │  Gera embeddings
│  output: Vector Store               │  Carrega ChromaDB
└─────────────────────────────────────┘
```

### Estrutura de cada asset

```python
@dg.asset(name="riotur_category_links", tags={"layer": "raw"})
def riotur_category_links(context):
    """Extrai 407 URLs de 18 categorias."""
    all_links = extract_all_categories_sync()
    ...
    return all_links  # → próximo asset recebe via parâmetro
```

---

## Quick Start

### 1. Pré-requisitos

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- Git

### 2. Setup

```bash
git clone <repo-url>
cd rio-tourism-ai-agent

# Instalar dependências (cria a venv em .venv/, dentro do projeto)
poetry install

# Instalar Chromium para Playwright
poetry run playwright install chromium

# Configurar ambiente
cp .env.example .env
# Editar .env com suas chaves
```

> A venv fica em `.venv/` (configurado em `poetry.toml`). Ative com
> `poetry shell` ou rode comandos direto com `poetry run <comando>`.

### 3. Executar ETL

#### Opção A: Interface gráfica do Dagster (recomendado)

**Antes da primeira execução**, defina `DAGSTER_HOME` para que o histórico de materializações
sobreviva entre sessões (sem isso o Dagster grava num diretório `tmpXXXX/` descartável e perde
tudo ao fechar). Use **caminho absoluto** — o Dagster não aceita relativo:

```powershell
# PowerShell (Windows) - permanente, vale para novos terminais
setx DAGSTER_HOME "C:\caminho\para\rio-tourism-ai-agent\1_etl_ingestao\.dagster_home"
```

> Para valer só na sessão atual do PowerShell, use
> `$env:DAGSTER_HOME = "...\1_etl_ingestao\.dagster_home"`.
> No Linux/Mac: `export DAGSTER_HOME="$(pwd)/1_etl_ingestao/.dagster_home"`.
> O diretório é criado automaticamente se não existir.

Abrir a UI web — rodar **de dentro de `1_etl_ingestao/`**, porque `run_etl.py` importa
os módulos por caminho relativo a essa pasta:

```bash
cd 1_etl_ingestao
poetry run dagster dev -f run_etl.py --use-legacy-code-server-behavior
```

> A flag `--use-legacy-code-server-behavior` é **necessária no Windows**: sem ela o `dagster dev`
> cria um workspace temporário e o mantém aberto enquanto passa o caminho para o daemon e o
> webserver — no Windows outro processo não consegue reabrir esse arquivo, e os dois subprocessos
> morrem com `PermissionError`. No Linux/Mac a flag é dispensável.

Acessar **http://localhost:3000** e, na aba **Assets**, clicar em **Materialize all**.
Isso roda os 4 assets em ordem e termina inserindo os dados no ChromaDB:

```
riotur_category_links → riotur_item_details → riotur_documents → chromadb_turismo_rio
```

Para carregar **apenas** o ChromaDB (quando os dados brutos já foram extraídos),
selecione o asset `chromadb_turismo_rio` no grafo e clique em **Materialize selected**.

> A UI continua rodando no terminal até você parar com `Ctrl+C`.
> Os JSONs intermediários são gravados em `data_raw/` (fora do Git, regenerados pelo ETL)
> e o banco vetorial no caminho de `CHROMA_DB_PATH`. Se o projeto estiver numa pasta
> sincronizada (OneDrive etc.), use um caminho absoluto fora dela — ver `.env.example`.

#### Opção B: Linha de comando (sem UI)

```bash
cd 1_etl_ingestao
dagster asset materialize -f run_etl.py --select "*"
```

> Não rode o agente enquanto o asset `chromadb_turismo_rio` estiver carregando.

### 4. Conversar com o Agente

```bash
python 2_agente_app/main.py                     # conversa nova (mostra o id para retomar)
python 2_agente_app/main.py --thread <id>       # retoma uma conversa anterior
```

O agente lembra o que foi dito na conversa: o histórico fica salvo em SQLite no
caminho de `AGENT_MEMORY_PATH`. No chat, digite `sair` para encerrar ou `/apagar`
para apagar a conversa atual.

Com `TAVILY_API_KEY` no `.env` (opcional, plano gratuito em https://app.tavily.com),
o agente também busca na web informação atual que não está na base (eventos,
acessibilidade, se um lugar ainda funciona), sempre citando a fonte.

O agente também consulta a previsão do tempo do Rio (até 16 dias à frente) pelo
Open-Meteo, que não exige chave, para sugerir praia ou um plano B coberto.

---

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `OPENROUTER_API_KEY` | Chave do provedor LLM (OpenRouter) | Sim |
| `OPENWEATHER_API_KEY` | API de clima em tempo real | Não |
| `GOOGLE_PLACES_API_KEY` | API de locais do Google | Não |
| `CHROMA_DB_PATH` | Caminho do banco vetorial | Sim (padrão: `./chroma_db_rio`) |
| `ENVIRONMENT` | `development` ou `production` | Sim |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Sim (padrão: `INFO`) |

---

## Estrutura de Pastas

```
rio-tourism-ai-agent/
│
├── 1_etl_ingestao/                    ← Pipeline ETL (Bounded Context 1)
│   ├── run_etl.py                     ← Assets Dagster + entry point
│   ├── document_transformer.py        ← JSON → texto corrido
│   ├── loader.py                      ← ChromaDB (embeddings + persistência)
│   └── extractors/
│       └── riotur/
│           ├── category_links_extractor.py   ← Playwright
│           └── item_details_extractor.py     ← Requests + BS4
│
├── 2_agente_app/                      ← Agente IA (Bounded Context 2)
│   ├── main.py                        ← Entry point
│   ├── domain/                        ← Entidades de negócio
│   ├── ports/                         ← Interfaces (contratos)
│   ├── adapters/                      ← Implementações concretas
│   └── graph/                         ← LangGraph (orquestração)
│
├── data_raw/                          ← Dados de saída do ETL
│   ├── riotur_links.json              ← 407 links
│   ├── riotur_details.json            ← 407 itens com detalhes
│   └── riotur_documents.json          ← 214 docs prontos p/ embedding
│
├── chroma_db_rio/                     ← Persistência ChromaDB
│
├── .env.example                       ← Template de variáveis
├── pyproject.toml                     ← Dependências Python (Poetry)
├── AGENTS.md                          ← Instruções para devs/IA
└── README.md                          ← Este arquivo
```

---

## Padrões e Convenções

| Regra | Detalhe |
|---|---|
| **Código** | Inglês (variáveis, funções, classes, módulos) |
| **Comentários** | Português BR (docstrings, inline, commits) |
| **Variáveis** | Substantivos descritivos (`tourist_spots`, `category_urls`) |
| **Funções** | Verbos de ação (`extract_address()`, `clean_phone_list()`) |
| **Type hints** | Obrigatórios em toda função pública |
| **Logging** | `logging.getLogger(__name__)`, sem emojis, `.format()` |
| **Commits** | `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` |

> Veja [AGENTS.md](AGENTS.md) para o guia completo de desenvolvimento.

---

## Design Patterns em Uso

| Pattern | Exemplo | Propósito |
|---|---|---|
| **Strategy** | Parsers por campo (telefone, endereço) | Estratégias intercambiáveis |
| **Template Method** | `generate_document_o_que_fazer()` | Estrutura comum, variação por seção |
| **Adapter** | `ChromaDBAdapter` | Isolar dependência externa |
| **Facade** | `extract_all_categories_sync()` | Interface simples sobre Playwright assíncrono |
| **Factory** | `generate_document(item)` | Seleciona template por seção |
| **Dependency Injection** | Assets Dagster | Dados fluem via parâmetros |
| **Chain of Responsibility** | `extract_hours()` | Tenta múltiplas estratégias em sequência |

---

## Troubleshooting

### `BrowserType.launch: Executable doesn't exist at ...headless_shell.exe`

O Chromium do Playwright não foi baixado para a venv deste projeto. Rode:

```bash
poetry run playwright install chromium
```

> Browsers já presentes em `%LOCALAPPDATA%\ms-playwright\` com **outro número de build**
> (ex.: `chromium-1234` quando o erro pede `1155`) foram instalados por outra versão do
> Playwright e **não** são reaproveitados — o projeto está pinado em `playwright==1.50.0`,
> que exige o build correspondente.

### `PermissionError: [Errno 13] Permission denied: ...\Temp\tmpXXXXXXXX`

Acontece ao rodar `dagster dev` no **Windows**; o sintoma visível é o processo encerrar com
`dagster-webserver process shut down unexpectedly with return code 1`.

É um bug do `dagster dev`: ele cria o workspace temporário com `NamedTemporaryFile` e mantém o
arquivo **aberto** enquanto passa o caminho para o daemon e para o webserver. No Windows um
arquivo temporário aberto não pode ser reaberto por outro processo, então os dois subprocessos
morrem. Rode com a flag que dispensa esse arquivo:

```bash
poetry run dagster dev -f run_etl.py --use-legacy-code-server-behavior
```

---

## Licença

Projeto de TCC (Trabalho de Conclusão de Curso).

---

**Última atualização:** Agosto 2026
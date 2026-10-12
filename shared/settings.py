"""Configuracao compartilhada entre o pipeline ETL e o agente.

Importar este modulo carrega o .env da raiz do projeto. O carregamento fica aqui,
e nao em cada consumidor, porque as variaveis sao lidas em pontos espalhados
(CHROMA_DB_PATH no shared/vector_store.py, OPENROUTER_* no adapter do OpenRouter)
e todos eles passam por aqui direta ou indiretamente.

O caminho e ancorado na raiz via Path(__file__): o ETL roda de dentro de
1_etl_ingestao/ e o agente da raiz, entao depender do diretorio atual faria o .env
ser encontrado so as vezes. Variaveis ja definidas no ambiente tem prioridade
sobre o arquivo (override=False), que e o comportamento esperado em producao.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)

COLLECTION_NAME = "riotur"

# Modelo de embedding da base vetorial.
#
# Diferente do modelo do LLM, trocar este valor **invalida a base**: vetores de
# modelos distintos nao sao comparaveis, e a collection precisa ser recriada e
# recarregada. O ChromaVectorStore detecta a troca e recria sozinho, mas isso
# significa que um valor errado aqui apaga os documentos ja indexados.
#
# O padrao tem janela de 512 tokens, que cobre a base inteira sem truncar.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "intfloat/multilingual-e5-small"

"""
Entrypoint local/manual do agente (uso via linha de comando/teste por enquanto)
"""

import logging
from typing import List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from composition import get_agent_graph
from graph.prompts import TOURISM_AGENT_SYSTEM_PROMPT


def handle_message(user_message: str, history: Optional[List[BaseMessage]] = None) -> str:
    """Recebe uma mensagem do usuario e retorna a resposta final do agente"""
    messages = list(history) if history else [SystemMessage(content=TOURISM_AGENT_SYSTEM_PROMPT)]
    messages.append(HumanMessage(content=user_message))
    result = get_agent_graph().invoke({"messages": messages})
    return result["messages"][-1].content


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # print aqui e a saida do script de linha de comando, nao log de producao
    answer = handle_message("Vou passar só um domingo no Rio com minha avó, que usa cadeira de rodas, e meu filho vegetariano de 8 anos. Quero ver o pôr do sol em algum lugar bonito, almoçar antes perto de lá e fugir de lugar muito cheio. Chove às vezes à tarde nessa época, então me dá um plano B coberto também. O que você sugere?")
    print(answer)

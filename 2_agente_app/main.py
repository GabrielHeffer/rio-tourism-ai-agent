"""
Entrypoint local do agente: chat no terminal com memoria de conversa

Cada conversa e identificada por um thread_id. O historico fica salvo no
checkpointer (SQLite), entao rodar de novo com --thread <id> retoma a conversa.
"""

import argparse
import logging
import os
import uuid

from langchain_core.messages import HumanMessage

from composition import delete_conversation, get_agent_graph

EXIT_COMMANDS = {"sair", "exit", "quit"}
DELETE_COMMAND = "/apagar"


def handle_message(user_message: str, thread_id: str) -> str:
    """Envia a mensagem do usuario para a conversa thread_id e retorna a resposta final do agente.

    So a mensagem nova e enviada: o historico da conversa e carregado pelo
    checkpointer a partir do thread_id.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = get_agent_graph().invoke({"messages": [HumanMessage(content=user_message)]}, config)
    return result["messages"][-1].content


def parse_arguments() -> argparse.Namespace:
    """Le os argumentos de linha de comando do chat"""
    parser = argparse.ArgumentParser(description="Chat com o assistente de turismo do Rio")
    parser.add_argument(
        "--thread",
        help="id de uma conversa anterior para retomar (sem ele, comeca uma conversa nova)",
    )
    return parser.parse_args()


def run_chat(thread_id: str) -> None:
    """Loop do chat no terminal ate o usuario sair ou apagar a conversa"""
    # print aqui e a interface do chat de linha de comando, nao log de producao
    print("Conversa: {}  (para retomar: --thread {})".format(thread_id, thread_id))
    print("Digite 'sair' para encerrar ou '{}' para apagar esta conversa.\n".format(DELETE_COMMAND))

    while True:
        user_message = input("Você: ").strip()
        if not user_message:
            continue
        if user_message.lower() in EXIT_COMMANDS:
            break
        if user_message.lower() == DELETE_COMMAND:
            delete_conversation(thread_id)
            print("Conversa apagada.")
            break
        print("\nAgente: {}\n".format(handle_message(user_message, thread_id)))


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING").upper())
    arguments = parse_arguments()
    run_chat(arguments.thread or str(uuid.uuid4()))

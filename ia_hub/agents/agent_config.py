import os
from langchain_core.messages import SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver
from .tools import (
    retrieve_availability_and_prices,
    look_for_information_that_i_don_t_know,
)


def get_tools():
    """Retorna a lista de ferramentas disponíveis para o agente."""
    return [
        retrieve_availability_and_prices,
        look_for_information_that_i_don_t_know,
    ]


def get_model():
    """Configura e retorna o modelo de chat."""
    return init_chat_model(model="gpt-4")


def get_checkpointer():
    """Cria e retorna o checkpointer PostgreSQL."""
    return PostgresSaver.from_conn_string(os.getenv("POSTGRES_URL", ""))


def create_agent_executor(checkpointer):
    """Cria o executor do agente com as ferramentas e checkpoint."""
    model = get_model()
    tools = get_tools()

    return create_react_agent(
        model=model,
        tools=tools,
        prompt=SystemMessage(
            content="""
                Você é um agente de IA especializado em atendimento ao cliente para uma pousada. Seu principal objetivo é responder perguntas sobre disponibilidade, preços de acomodações e serviços oferecidos. Caso não saiba alguma informação, utilize as ferramentas disponíveis para buscar detalhes atualizados sobre a empresa em que você atua. Sempre priorize respostas precisas, claras e úteis, com foco na experiência do hóspede.
            """
        ),
        checkpointer=checkpointer,
    )

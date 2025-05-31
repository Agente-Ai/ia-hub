import os
from datetime import datetime
from zoneinfo import ZoneInfo
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
            content=f"""
                Data atual: {datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()}
            """,
        ),
        checkpointer=checkpointer,
    )

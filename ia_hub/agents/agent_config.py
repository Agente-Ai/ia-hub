import os
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage
from .tools import (
    retrieve_availability_and_prices,
    look_for_information_that_i_don_t_know,
)
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately


def get_model():
    """Configura e retorna o modelo de chat."""
    return init_chat_model(model="gpt-4")


DEFAULT_INITIAL_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("placeholder", "{messages}"),
        ("user", "Crie um resumo da conversa acima:"),
    ]
)

DEFAULT_EXISTING_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("placeholder", "{messages}"),
        (
            "user",
            "Este é o resumo da conversa até agora: {existing_summary}\n\n"
            "Estenda este resumo levando em consideração as novas mensagens acima:",
        ),
    ]
)

DEFAULT_FINAL_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("placeholder", "{system_message}"),
        ("system", "Resumo da conversa até agora: {summary}"),
        ("placeholder", "{messages}"),
    ]
)

prompt_summarization = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content="Resuma a conversa atual."),
        HumanMessage(content="{messages}"),
    ]
)

summarization_node = SummarizationNode(
    model=get_model(),
    max_tokens=384,
    max_tokens_before_summary=5000,
    output_messages_key="messages",
    token_counter=count_tokens_approximately,
    final_prompt=DEFAULT_FINAL_SUMMARY_PROMPT,
    initial_summary_prompt=DEFAULT_INITIAL_SUMMARY_PROMPT,
    existing_summary_prompt=DEFAULT_EXISTING_SUMMARY_PROMPT,
)


def get_tools():
    """Retorna a lista de ferramentas disponíveis para o agente."""
    return [
        retrieve_availability_and_prices,
        look_for_information_that_i_don_t_know,
    ]


def get_checkpointer():
    """Cria e retorna o checkpointer PostgreSQL."""
    return PostgresSaver.from_conn_string(os.getenv("POSTGRES_URL", ""))


def create_agent_executor(checkpointer: PostgresSaver):
    """Cria o executor do agente com as ferramentas e checkpoint."""
    checkpointer.setup()

    model = get_model()
    tools = get_tools()

    return create_react_agent(
        model=model,
        tools=tools,
        prompt=SystemMessage(
            content=(
                f"Data atual: "
                f"{datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()}"
            )
        ),
        pre_model_hook=summarization_node,
        checkpointer=checkpointer,
        debug=True,
    )


def get_agent_executor_with_context():
    """Cria e retorna o agent_executor gerenciando o contexto do checkpointer."""
    with get_checkpointer() as checkpointer:
        agent_executor = create_agent_executor(checkpointer)
        return agent_executor, checkpointer


def execute_with_agent(callback, *args, **kwargs):
    """Executa uma função passando o agent_executor como primeiro parâmetro.

    Args:
        callback: Função que recebe agent_executor como primeiro argumento
        *args, **kwargs: Argumentos adicionais para a função callback

    Returns:
        O resultado da execução da função callback
    """
    with get_checkpointer() as checkpointer:
        agent_executor = create_agent_executor(checkpointer)
        return callback(agent_executor, *args, **kwargs)

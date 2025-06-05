"""Prompts e configurações de resumo para o agente."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langmem.short_term import SummarizationNode


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


def get_summarization_node(model):
    """Cria e retorna o nó de resumo configurado."""
    return SummarizationNode(
        model=model,
        max_tokens=384,
        max_tokens_before_summary=5000,
        output_messages_key="messages",
        token_counter=count_tokens_approximately,
        final_prompt=DEFAULT_FINAL_SUMMARY_PROMPT,
        initial_summary_prompt=DEFAULT_INITIAL_SUMMARY_PROMPT,
        existing_summary_prompt=DEFAULT_EXISTING_SUMMARY_PROMPT,
    )

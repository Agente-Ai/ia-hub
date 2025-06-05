"""Configuração do agente - Compatibilidade com código legado."""

# Importações para compatibilidade com código existente
from .agent_factory import agent_factory


# Funções de compatibilidade para código legado
def get_checkpointer():
    """Compatibilidade: Cria e retorna o checkpointer PostgreSQL."""
    return agent_factory.get_checkpointer()


def create_agent_executor(checkpointer=None):
    """Compatibilidade: Cria o executor do agente."""
    return agent_factory.create_agent_executor(checkpointer)


def execute_with_agent(callback, *args, **kwargs):
    """Compatibilidade: Executa uma função passando o agent_executor."""
    return agent_factory.execute_with_agent(callback, *args, **kwargs)

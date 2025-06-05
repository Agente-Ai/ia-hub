"""Factory para criação e configuração de agentes."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import SystemMessage

from .tools import get_tools
from .prompts import get_summarization_node


class AgentFactory:
    """Factory para criação de agentes com configurações centralizadas."""
    
    _instance = None
    _agent_executor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def get_model():
        """Configura e retorna o modelo de chat."""
        return init_chat_model(model="gpt-4")
    
    @staticmethod
    def get_checkpointer() -> Optional[PostgresSaver]:
        """Cria e retorna o checkpointer PostgreSQL."""
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            return None
        
        try:
            return PostgresSaver.from_conn_string(postgres_url)
        except Exception as e:
            print(f"Erro ao criar checkpointer: {e}")
            return None
    
    def create_agent_executor(self, checkpointer: Optional[PostgresSaver] = None):
        """Cria o executor do agente com as ferramentas e checkpoint."""
        if checkpointer:
            checkpointer.setup()

        model = self.get_model()
        tools = get_tools()
        summarization_node = get_summarization_node(model)

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
    
    def get_agent_executor(self):
        """Retorna uma instância singleton do agent_executor."""
        if self._agent_executor is None:
            checkpointer = self.get_checkpointer()
            self._agent_executor = self.create_agent_executor(checkpointer)
        return self._agent_executor
    
    def execute_with_agent(self, callback, *args, **kwargs):
        """Executa uma função passando o agent_executor como primeiro parâmetro.

        Args:
            callback: Função que recebe agent_executor como primeiro argumento
            *args, **kwargs: Argumentos adicionais para a função callback

        Returns:
            O resultado da execução da função callback
        """
        checkpointer = self.get_checkpointer()
        if checkpointer:
            with checkpointer as cp:
                agent_executor = self.create_agent_executor(cp)
                return callback(agent_executor, *args, **kwargs)
        else:
            agent_executor = self.create_agent_executor()
            return callback(agent_executor, *args, **kwargs)


# Instância singleton
agent_factory = AgentFactory()

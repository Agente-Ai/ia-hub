"""Gerenciador de sessões e configurações do agente."""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SessionConfig:
    """Configuração de sessão do agente."""

    thread_id: str
    owner_id: str

    @property
    def config_dict(self) -> Dict[str, Any]:
        """Retorna a configuração como dicionário."""
        return {
            "configurable": {
                "thread_id": self.thread_id,
                "owner_id": self.owner_id,
            }
        }


class SessionManager:
    """Gerencia sessões ativas do agente."""

    def __init__(self):
        self._sessions: Dict[str, SessionConfig] = {}

    def create_session(
        self, thread_id: str = "default_thread", owner_id: str = "default_owner"
    ) -> SessionConfig:
        """Cria uma nova sessão."""
        session = SessionConfig(thread_id=thread_id, owner_id=owner_id)
        self._sessions[thread_id] = session
        return session


# Instância singleton
session_manager = SessionManager()

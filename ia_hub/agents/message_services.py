"""Serviços para processamento de mensagens do WhatsApp."""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from .agent_factory import agent_factory
from .session_manager import SessionConfig


class WhatsAppMessageProcessor:
    """Processa mensagens do WhatsApp Business API."""

    @staticmethod
    def extract_message_content(payload: Dict[str, Any]) -> Optional[str]:
        """Extrai o conteúdo da mensagem do payload do WhatsApp."""
        try:
            entries = payload.get("entry", [])
            entry = entries[0] if entries else {}
            changes = entry.get("changes", [])
            change = changes[0] if changes else {}
            value = change.get("value", {})

            messages = value.get("messages", [])
            message = messages[0] if messages else {}
            text = message.get("text", {})
            content = text.get("body", "")

            return content if content.strip() else None
        except (IndexError, KeyError, AttributeError):
            return None

    def process_single_message(
        self, payload: Dict[str, Any], session_config: SessionConfig
    ) -> Dict[str, Any]:
        """Processa uma única mensagem do WhatsApp."""
        content = self.extract_message_content(payload)

        def _execute_single_chat(agent_executor):
            return agent_executor.invoke(
                {"messages": [HumanMessage(content=content)]},
                session_config.config_dict,
            )

        return agent_factory.execute_with_agent(_execute_single_chat)


class InteractiveChatService:
    """Serviço para chat interativo."""

    def start_interactive_chat(self, session_config: SessionConfig):
        """Inicia um loop de conversa interativa."""
        print("Iniciando chat interativo (Ctrl+C ou Ctrl+D para sair)")
        print("-" * 50)

        def _execute_interactive_chat(agent_executor):
            while True:
                try:
                    user_input = input("Você: ")
                    if not user_input.strip():
                        continue

                    print("\nAgente:")
                    for step in agent_executor.stream(
                        {"messages": [HumanMessage(content=user_input)]},
                        session_config.config_dict,
                        stream_mode="values",
                    ):
                        step["messages"][-1].pretty_print()

                    print("-" * 50)

                except (KeyboardInterrupt, EOFError):
                    print("\nEncerrando...")
                    break

        agent_factory.execute_with_agent(_execute_interactive_chat)

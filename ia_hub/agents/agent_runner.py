"""Runner principal para execução do agente."""

from .session_manager import session_manager
from .message_services import WhatsAppMessageProcessor, InteractiveChatService


class AgentRunner:
    """Classe para executar o agente de forma interativa."""

    def __init__(self, thread_id="default_thread", owner_id="default_owner"):
        self.session_config = session_manager.create_session(thread_id, owner_id)
        self.whatsapp_processor = WhatsAppMessageProcessor()
        self.interactive_service = InteractiveChatService()

    def chat_single(self, payload: dict):
        """Executa uma única mensagem e retorna a resposta."""
        return self.whatsapp_processor.process_single_message(
            payload, self.session_config
        )

    def chat_interactive(self):
        """Inicia um loop de conversa interativa."""
        self.interactive_service.start_interactive_chat(self.session_config)

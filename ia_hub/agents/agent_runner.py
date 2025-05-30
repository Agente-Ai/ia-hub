from langchain_core.messages import HumanMessage
from .agent_config import get_checkpointer, create_agent_executor


class AgentRunner:
    """Classe para executar o agente de forma interativa."""

    def __init__(self, thread_id="default_thread", owner_id="default_owner"):
        self.owner_id = owner_id
        self.thread_id = thread_id
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
                "owner_id": self.owner_id,
            }
        }

    def chat_single(self, payload: dict):
        """Executa uma única mensagem e retorna a resposta."""
        with get_checkpointer() as checkpointer:
            checkpointer.setup()

            agent_executor = create_agent_executor(checkpointer)

            entries = payload.get("entry", [])
            entry = entries[0] if entries else {}
            changes = entry.get("changes", [])
            change = changes[0] if changes else {}
            value = change.get("value", {})

            messages = value.get("messages", [])
            message = messages[0] if messages else {}
            text = message.get("text", {})
            content = text.get("body", "")

            responses = agent_executor.invoke(
                {
                    "messages": [HumanMessage(content=content)],
                },
                self.config,
            )

            return responses

    def chat_interactive(self):
        """Inicia um loop de conversa interativa."""
        print("Iniciando chat interativo (Ctrl+C ou Ctrl+D para sair)")
        print("-" * 50)

        with get_checkpointer() as checkpointer:
            checkpointer.setup()

            agent_executor = create_agent_executor(checkpointer)

            while True:
                try:
                    user_input = input("Você: ")
                    if not user_input.strip():
                        continue

                    print("\nAgente:")
                    for step in agent_executor.stream(
                        {"messages": [HumanMessage(content=user_input)]},
                        self.config,
                        stream_mode="values",
                    ):
                        step["messages"][-1].pretty_print()

                    print("-" * 50)

                except (KeyboardInterrupt, EOFError):
                    print("\nEncerrando...")
                    break

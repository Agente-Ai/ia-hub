from .agent_config import execute_with_agent
from langchain_core.messages import HumanMessage


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

        def _execute_single_chat(agent_executor):
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
                    "messages": [
                        HumanMessage(content=content),
                    ],
                },
                self.config,
            )

            return responses

        return execute_with_agent(_execute_single_chat)

    def chat_interactive(self):
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
                        self.config,
                        stream_mode="values",
                    ):
                        step["messages"][-1].pretty_print()

                    print("-" * 50)

                except (KeyboardInterrupt, EOFError):
                    print("\nEncerrando...")
                    break

        execute_with_agent(_execute_interactive_chat)

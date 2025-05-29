from agent_runner import AgentRunner


def main():
    """Função principal para executar o agente."""
    # Criar o runner do agente
    runner = AgentRunner()

    # Iniciar chat interativo
    runner.chat_interactive()


if __name__ == "__main__":
    main()

"""
Camada de consumidor RabbitMQ pronta para produção.
"""

import os
import json
import pika
import logging
import threading
from dotenv import load_dotenv
from ia_hub.agents.agent_service import process_and_publish

load_dotenv()

RABBITMQ_INPUT_QUEUE = os.getenv("RABBITMQ_INPUT_QUEUE", "incoming.messages")
RABBITMQ_OUTPUT_QUEUE = os.getenv("RABBITMQ_OUTPUT_QUEUE", "messages.to_send")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)


def main():
    logging.info(f"Conectando ao RabbitMQ em {RABBITMQ_URL}...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))

    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_INPUT_QUEUE, durable=True)
    channel.queue_declare(queue=RABBITMQ_OUTPUT_QUEUE, durable=True)

    logging.info(f"Aguardando mensagens na fila '{RABBITMQ_INPUT_QUEUE}'...")

    def callback(ch, method, properties, body):
        logging.info(f"Mensagem recebida: {body}")

        try:
            data = json.loads(body)

            thread = threading.Thread(target=process_and_publish, args=(data,))
            thread.start()
        except Exception as e:
            logging.exception("Erro ao processar mensagem:")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

        logging.info("Processamento delegado para thread.")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_INPUT_QUEUE, on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logging.info("Encerrando consumidor RabbitMQ...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()

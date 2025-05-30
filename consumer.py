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
    logging.info("Conectando ao RabbitMQ em %s...", RABBITMQ_URL)
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))

    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_INPUT_QUEUE, durable=True)
    channel.queue_declare(queue=RABBITMQ_OUTPUT_QUEUE, durable=True)

    logging.info("Aguardando mensagens na fila '%s'...", RABBITMQ_INPUT_QUEUE)

    def callback(ch, method, properties, body):
        logging.info("Mensagem recebida: %s, properties: %s", body, properties)

        try:
            data = json.loads(body)

            process_and_publish(data)

            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError:
            logging.exception("Erro ao decodificar JSON da mensagem:")
        except pika.exceptions.AMQPError:
            logging.exception("Erro no RabbitMQ ao processar mensagem:")
        except Exception:
            logging.exception("Erro inesperado ao processar mensagem:")
            raise
        finally:
            logging.info("Mensagem processada e confirmada.")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=RABBITMQ_INPUT_QUEUE,
        on_message_callback=callback,
    )

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logging.info("Encerrando consumidor RabbitMQ...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()

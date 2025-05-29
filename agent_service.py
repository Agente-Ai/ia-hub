import os
import json
import pika
from dotenv import load_dotenv
from agent_runner import AgentRunner

load_dotenv()

RABBITMQ_OUTPUT_QUEUE = os.getenv("RABBITMQ_OUTPUT_QUEUE", "messages.to_send")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


def process_and_publish(user_message):
    """Processa a mensagem com a IA e publica a resposta na fila de output."""
    entries = user_message.get("entry", [])
    entry = entries[0] if entries else {}
    changes = entry.get("changes", [])
    change = changes[0] if changes else {}
    value = change.get("value", {})
    metadata = value.get("metadata", {})
    contacts = value.get("contacts", [])
    contact = contacts[0] if contacts else {}

    wa_id = contact.get("wa_id", None)
    display_phone_number = metadata.get("display_phone_number", None)

    thread_id = f"{display_phone_number}.{wa_id}"

    runner = AgentRunner(thread_id=thread_id)
    responses = runner.chat_single(user_message)

    body = responses.get("messages")[-1].content
    result = {
        **user_message,
        "content": {
            "text": {
                "body": body,
            },
        },
    }

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_OUTPUT_QUEUE, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=RABBITMQ_OUTPUT_QUEUE,
        body=json.dumps(result),
        properties=pika.BasicProperties(
            delivery_mode=2,
        ),
    )
    connection.close()

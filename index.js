import amqp from "amqplib";
import dotenv from "dotenv";
import express from "express";
import router from "./http.js";
import { processMessage } from './services/aiProcessor.js';

dotenv.config();

const app = express();

app.use(express.json());

app.get('/', (req, res) => res.status(200).send('ok'));

app.use("/api", router);

app.listen(process.env.PORT || 4000, () => {
    console.log(`Server is listening on port: ${process.env.PORT || 4000}`);
});

(async () => {
    const INPUT_QUEUE = "incoming.messages";
    const OUTPUT_QUEUE = "messages.to_send";

    let connection, channel;

    try {
        connection = await amqp.connect(process.env.RABBITMQ_URL || "amqp://localhost");
        channel = await connection.createChannel();

        // Ensure the input and output queues exist
        await channel.assertQueue(INPUT_QUEUE, { durable: true });
        await channel.assertQueue(OUTPUT_QUEUE, {
            durable: true
        });

        // Consume messages from the input queue
        channel.consume(
            INPUT_QUEUE,
            async (msg) => {
                if (!msg) return;

                const entry = JSON.parse(msg.content.toString());

                // Process the message using the IA module
                const processedMessageContent = await processMessage(entry);

                // Process the message (example: add a processed flag)
                const processedMessage = {
                    ...processedMessageContent,
                    processed: true,
                    timestamp: new Date().toISOString(),
                };

                // Publish the processed message to the output queue
                channel.sendToQueue(OUTPUT_QUEUE, Buffer.from(JSON.stringify(processedMessage)), {
                    persistent: true,
                });

                // Acknowledge the message
                channel.ack(msg);
            },
            { noAck: false }
        );
    } catch (error) {
        console.error("Failed to connect to RabbitMQ or process messages:", error);
        if (connection) {
            await connection.close();
        }
        process.exit(1);
    }
})();
import pg from "pg";

import {
    ChatPromptTemplate,
    MessagesPlaceholder,
} from "@langchain/core/prompts";
import { ChatOpenAI } from "@langchain/openai";
import {
    RunnableWithMessageHistory,
    RunnablePassthrough,
} from "@langchain/core/runnables";
import { PostgresChatMessageHistory } from "@langchain/community/stores/message/postgres";
import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";
import { OpenAIEmbeddings } from "@langchain/openai";

let sharedPool;

const getPool = () => {
    if (!sharedPool) {
        sharedPool = new pg.Pool({
            port: 5432,
            database: "postgres",
            host: process.env.DB_HOST || "postgres",
            user: process.env.DB_USER || "postgres",
            password: process.env.DB_PASSWORD || "postgres",
            idleTimeoutMillis: 10000,
            connectionTimeoutMillis: 5000,
        });

        sharedPool.on("error", (err) => {
            console.error("Unexpected error on idle client", err);
        });
    }
    return sharedPool;
};

export const processMessage = async ({ entry }) => {
    const value_message = entry?.[0]?.changes[0]?.value;
    const message = value_message?.messages?.[0];
    const metadata = value_message?.metadata;

    console.log('Processing message', message);

    const pool = getPool();

    const embeddings = new OpenAIEmbeddings({ model: "text-embedding-3-small" });

    const vectorStore = await PGVectorStore.initialize(embeddings, {
        pool,
        verbose: true,
        tableName: "embeddings",
        columns: {
            idColumnName: "id",
            vectorColumnName: "vector",
            contentColumnName: "content",
            metadataColumnName: "metadata",
        },
        distanceStrategy: "cosine",
    });

    const retriever = vectorStore.asRetriever({
        k: 3,
        filter: { businessPhoneId: metadata.display_phone_number },
    });

    const prompt = ChatPromptTemplate.fromMessages([
        new MessagesPlaceholder("chat_history"),
        ["system", "{context}"],
        ["human", "{input}"],
    ]);

    const model = new ChatOpenAI({ temperature: 0 });

    const ragChain = RunnablePassthrough.assign({
        context: async (input) => {
            const docs = await retriever.invoke(input.input);
            return docs.map((doc) => doc.pageContent).join("\n\n");
        },
    }).pipe(prompt).pipe(model);

    const chainWithHistory = new RunnableWithMessageHistory({
        runnable: ragChain,
        inputMessagesKey: "input",
        historyMessagesKey: "chat_history",
        getMessageHistory: async (sessionId) =>
            new PostgresChatMessageHistory({ sessionId, pool }),
    });

    const response = await chainWithHistory.invoke(
        {
            input: message.text.body,
        },
        {
            configurable: {
                callbacks: [
                    {
                        handleLLMStart: async (llm, inputs) => {
                            console.log("LLM started:", { llm, inputs });
                        },
                        handleLLMEnd: async (output) => {
                            console.log("LLM ended:", output);
                        },
                        handleChainStart: async (chain, inputs) => {
                            console.log("Chain started:", { chain, inputs });
                        },
                        handleChainEnd: async (output) => {
                            console.log("Chain ended:", output);
                        },
                        handleToolStart: async (tool, input) => {
                            console.log("Tool started:", { tool, input });
                        },
                        handleToolEnd: async (output) => {
                            console.log("Tool ended:", output);
                        },
                        handleError: async (err) => {
                            console.error("Callback error:", err);
                        },
                    },
                ],
                thread_id: message.from,
                sessionId: message.from,
            },
        }
    );

    console.log("Retung LLM response", response.response_metadata);

    return {
        ...message,
        text: { body: response.content },
        phone_number_id: metadata.phone_number_id,
    };
};

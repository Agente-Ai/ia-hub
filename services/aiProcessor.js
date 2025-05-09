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

let sharedPool = null;

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);
const error = (...args) => console.error(`[${new Date().toISOString()}]`, ...args);

const required = (name) => {
    const val = process.env[name];
    if (!val) throw new Error(`Missing required env var: ${name}`);
    return val;
};

const getPool = () => {
    if (!sharedPool) {
        log("Creating new Postgres pool...");

        sharedPool = new pg.Pool({
            host: required("DB_HOST"),
            user: required("DB_USER"),
            password: required("DB_PASSWORD"),
            database: required("DB_NAME"),
            port: Number(process.env.DB_PORT || 5432),
            max: Number(process.env.DB_MAX_CONNECTIONS || 10),
            idleTimeoutMillis: 10000,
            connectionTimeoutMillis: 5000,
            ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : undefined,
        });

        sharedPool.on("error", (err) => {
            error("Unexpected error on idle client", err);
        });

        process.on("SIGINT", async () => {
            log("Gracefully shutting down Postgres pool...");
            await sharedPool.end();
            process.exit(0);
        });

        setInterval(() => {
            const stats = {
                total: sharedPool.totalCount,
                idle: sharedPool.idleCount,
                waiting: sharedPool.waitingCount,
            };
            log("Postgres pool stats:", stats);
        }, 60000);
    }

    return sharedPool;
};

export const processMessage = async ({ entry }) => {
    const value_message = entry?.[0]?.changes[0]?.value;
    const message = value_message?.messages?.[0];
    const metadata = value_message?.metadata;

    log("Received new message:", {
        from: message?.from,
        text: message?.text?.body,
        phone_number_id: metadata?.phone_number_id,
    });

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
            log("Fetching relevant documents for input:", input.input);
            const docs = await retriever.invoke(input.input);
            log("Retrieved docs:", docs.map((d) => d.metadata?.id || "[no id]"));
            return docs.map((doc) => doc.pageContent).join("\n\n");
        },
    }).pipe(prompt).pipe(model);

    const chainWithHistory = new RunnableWithMessageHistory({
        runnable: ragChain,
        inputMessagesKey: "input",
        historyMessagesKey: "chat_history",
        getMessageHistory: async (sessionId) => {
            log("Loading chat history for session:", sessionId);
            return new PostgresChatMessageHistory({ sessionId, pool });
        },
    });

    log("Invoking chain with input:", message.text.body);

    const response = await chainWithHistory.invoke(
        { input: message.text.body },
        {
            configurable: {
                callbacks: [
                    {
                        handleLLMStart: async (llm, inputs) => log("LLM started:", { llm, inputs }),
                        handleLLMEnd: async (output) => log("LLM ended:", output),
                        handleChainStart: async (chain, inputs) => log("Chain started:", { chain, inputs }),
                        handleChainEnd: async (output) => log("Chain ended:", output),
                        handleToolStart: async (tool, input) => log("Tool started:", { tool, input }),
                        handleToolEnd: async (output) => log("Tool ended:", output),
                        handleError: async (err) => error("Callback error:", err),
                    },
                ],
                thread_id: message.from,
                sessionId: message.from,
            },
        }
    );

    log("Returning LLM response:", {
        response: response.content,
        metadata: response.response_metadata,
    });

    return {
        ...message,
        text: { body: response.content },
        phone_number_id: metadata.phone_number_id,
    };
};

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

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);
const error = (...args) => console.error(`[${new Date().toISOString()}]`, ...args);

const getPool = () => {
    if (!sharedPool) {
        log("Creating new Postgres pool...");
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
            error("Unexpected error on idle client", err);
        });
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

    log("Initializing OpenAI embeddings...");
    const embeddings = new OpenAIEmbeddings({ model: "text-embedding-3-small" });

    log("Setting up PGVectorStore...");
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

    log("Creating retriever with filter:", {
        businessPhoneId: metadata.display_phone_number,
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
            log("Retrieved docs:", docs.map(d => d.metadata?.id || "[no id]"));
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
        {
            input: message.text.body,
        },
        {
            configurable: {
                callbacks: [
                    {
                        handleLLMStart: async (llm, inputs) => {
                            log("LLM execution started:", { llm, inputs });
                        },
                        handleLLMEnd: async (output) => {
                            log("LLM execution ended:", output);
                        },
                        handleChainStart: async (chain, inputs) => {
                            log("Chain execution started:", { chain, inputs });
                        },
                        handleChainEnd: async (output) => {
                            log("Chain execution ended:", output);
                        },
                        handleToolStart: async (tool, input) => {
                            log("Tool started:", { tool, input });
                        },
                        handleToolEnd: async (output) => {
                            log("Tool ended:", output);
                        },
                        handleError: async (err) => {
                            error("Callback error:", err);
                        },
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

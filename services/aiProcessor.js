// Importa o módulo pg para conexão com o banco de dados PostgreSQL
import pg from "pg";

// Importa classes e funções do LangChain para prompts e processamento de mensagens
import {
    ChatPromptTemplate,
    MessagesPlaceholder,
} from "@langchain/core/prompts";
import { ChatOpenAI } from "@langchain/openai";
import { RunnableWithMessageHistory, RunnablePassthrough } from "@langchain/core/runnables";
import { PostgresChatMessageHistory } from "@langchain/community/stores/message/postgres";
import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";
import { OpenAIEmbeddings } from "@langchain/openai";

/**
 * Função principal para processar mensagens recebidas.
 * @param {Object} message - Mensagem recebida contendo informações como texto e remetente.
 * @returns {Object} - Mensagem processada com resposta gerada e timestamp.
 */
export const processMessage = async ({ entry }) => {
    const pool = new pg.Pool({
        port: 5432,
        database: "postgres",
        host: process.env.DB_HOST || "postgres",
        user: process.env.DB_USER || "postgres",
        password: process.env.DB_PASSWORD || "postgres",
    });

    pool.on("error", (err) => {
        console.error("Unexpected error on idle client", err);
        process.exit(-1);
    });

    const client = await pool.connect();
    try {
        await client.query(`SET statement_timeout = 5000;`);
    } catch (err) {
        console.error("Erro ao configurar statement_timeout", err);
        throw err;
    } finally {
        client.release();
    }

    // Função para garantir a criação da tabela 'embeddings'
    const ensureEmbeddingsTable = async () => {
        const client = await pool.connect();
        try {
            // Trava para que apenas uma instância execute a criação
            await client.query("SELECT pg_advisory_lock(424242);");

            // Verifica se a tabela 'embeddings' já existe no schema 'public'
            const res = await client.query(`
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'embeddings'
                );
            `);

            if (!res.rows[0].exists) {
                // Cria a tabela 'embeddings' caso não exista
                await client.query(`
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id TEXT PRIMARY KEY,
                        content TEXT,
                        metadata JSONB,
                        vector vector(1536)
                    );
                `);
            }

            // Libera o lock
            await client.query("SELECT pg_advisory_unlock(424242);");
        } catch (err) {
            console.error("Error ensuring embeddings table:", err);
            throw err;
        } finally {
            client.release();
        }
    };

    await ensureEmbeddingsTable();

    const embeddings = new OpenAIEmbeddings({
        model: "text-embedding-3-small",
    });

    const vectorStore = await PGVectorStore.initialize(embeddings, {
        postgresConnectionOptions: {
            port: 5432,
            type: "postgres",
            database: "postgres",
            host: process.env.DB_HOST || "postgres",
            user: process.env.DB_USER || "postgres",
            password: process.env.DB_PASSWORD || "postgres",
        },
        tableName: "embeddings",
        columns: {
            idColumnName: "id",
            vectorColumnName: "vector",
            contentColumnName: "content",
            metadataColumnName: "metadata",
        },
        distanceStrategy: "cosine",
    });

    const value_message = entry?.[0]?.changes[0]?.value;
    const message = value_message?.messages?.[0];
    const metadata = value_message?.metadata;

    const retriever = vectorStore.asRetriever({ k: 3, filter: { businessPhoneId: metadata.display_phone_number } });

    const prompt = ChatPromptTemplate.fromMessages([
        new MessagesPlaceholder("chat_history"),
        ["system", "{context}"],
        ["human", "{input}"],
    ]);

    const model = new ChatOpenAI({
        temperature: 0,
    });

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
        getMessageHistory: async (sessionId) => {
            return new PostgresChatMessageHistory({
                sessionId,
                pool,
            });
        },
    });

    const response = await chainWithHistory.invoke(
        {
            input: message.text.body,
        },
        {
            configurable: {
                thread_id: message.from,
                sessionId: message.from,
            },
        }
    );

    await pool.end();

    return {
        metadata,
        ...message,
        text: { body: response.content },
    };
};

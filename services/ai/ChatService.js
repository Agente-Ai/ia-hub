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

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);

export class ChatService {
    #pool;

    constructor(pool) {
        this.#pool = pool;
    }

    createChain(retriever, systemPrompt) {
        // Use default prompt if none provided
        const defaultPrompt = "Você é um assistente útil e amigável. Responda com base no contexto fornecido.";
        const finalSystemPrompt = systemPrompt || defaultPrompt;

        const prompt = ChatPromptTemplate.fromMessages([
            new MessagesPlaceholder("chat_history"),
            ["system", finalSystemPrompt],
            ["system", "{context}"],
            ["human", "{input}"],
        ]);

        const model = new ChatOpenAI({ temperature: 0 });

        const ragChain = RunnablePassthrough.assign({
            context: async (input) => {
                log("Buscando documentos para:", input.input);
                const docs = await retriever.invoke(input.input);
                log("Docs recuperados:", docs.map((d) => d || "Sem infos"));
                return docs.map((doc) => doc.pageContent).join("\n\n");
            },
        }).pipe(prompt).pipe(model);

        return ragChain;
    }

    createChainWithHistory(chain) {
        return new RunnableWithMessageHistory({
            runnable: chain,
            inputMessagesKey: "input",
            historyMessagesKey: "chat_history",
            getMessageHistory: async (sessionId) => {
                log("Carregando histórico para sessão:", sessionId);
                return new PostgresChatMessageHistory({ sessionId, pool: this.#pool });
            },
        });
    }

    async processUserMessage(chainWithHistory, message, sessionId) {
        log("Executando chain com:", message);

        return await chainWithHistory.invoke(
            { input: message },
            {
                configurable: {
                    thread_id: sessionId,
                    sessionId: sessionId,
                },
            }
        );
    }
}

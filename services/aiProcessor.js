import { PostgresConnection } from './db/PostgresConnection.js';
import { PromptRepository } from './repositories/PromptRepository.js';
import { VectorStoreService } from './ai/VectorStoreService.js';
import { ChatService } from './ai/ChatService.js';

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);
const error = (...args) => console.error(`[${new Date().toISOString()}]`, ...args);

export const processMessage = async (object) => {
    try {
        log("Iniciando processamento da mensagem...", object);

        const entry = object?.entry?.[0];
        const value_message = entry?.changes[0]?.value;
        const message = value_message?.messages?.[0];
        const metadata = value_message?.metadata;

        log("Mensagem recebida:", {
            from: message?.from,
            text: message?.text?.body,
            whatsapp_business_account_id: entry?.id,
            phone_number_id: metadata?.phone_number_id,
            display_phone_number: metadata?.display_phone_number,
        });

        // Inicializa as conexões e serviços
        const dbConnection = new PostgresConnection();
        const pool = dbConnection.getPool();

        // Busca o prompt personalizado da empresa
        const promptRepository = new PromptRepository(pool);
        const customPrompt = await promptRepository.getPromptByBusinessPhone(metadata.display_phone_number);

        if (customPrompt) {
            log("Usando prompt personalizado para empresa:", metadata.display_phone_number);
        } else {
            log("Usando prompt padrão (nenhum personalizado encontrado)");
        }

        // Inicializa o serviço de vetores e recupera documentos relevantes
        const vectorService = new VectorStoreService(pool);
        const retriever = await vectorService.createRetriever(metadata.display_phone_number);

        // Configura o serviço de chat
        const chatService = new ChatService(pool);
        const chain = chatService.createChain(retriever, customPrompt);
        const chainWithHistory = chatService.createChainWithHistory(chain);

        // Processa a mensagem do usuário
        const response = await chatService.processUserMessage(
            chainWithHistory,
            message.text.body,
            `${message.from} - ${display_phone_number}`,
        );

        log("Resposta do modelo:", {
            response: response.content,
            metadata: response.response_metadata,
        });

        return {
            ...message,
            content: {
                text: { body: response.content },
            },
            phone_number_id: metadata.phone_number_id,
            display_phone_number: metadata.display_phone_number,
            whatsapp_business_account_id: entry.id,
        };
    } catch (err) {
        error("Erro ao processar mensagem:", err);
        throw err;
    }
};

import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";
import { OpenAIEmbeddings } from "@langchain/openai";

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);

export class VectorStoreService {
    #pool;
    
    constructor(pool) {
        this.#pool = pool;
    }

    async createRetriever(businessPhoneId) {
        const embeddings = new OpenAIEmbeddings({ model: "text-embedding-3-small" });

        const vectorStore = await PGVectorStore.initialize(embeddings, {
            pool: this.#pool,
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

        return vectorStore.asRetriever({
            k: 10,
            filter: { businessPhoneId },
        });
    }
}

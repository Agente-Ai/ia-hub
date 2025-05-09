import { v4 as uuidv4 } from "uuid";
import { OpenAIEmbeddings } from "@langchain/openai";
import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";

export class EmbeddingsService {
    constructor() {
        this.embeddings = new OpenAIEmbeddings({
            model: "text-embedding-3-small",
        });

        this.config = {
            postgresConnectionOptions: {
                type: "postgres",
                host: "postgres",
                port: 5432,
                user: "postgres",
                password: "postgres",
                database: "postgres",
            },
            tableName: "embeddings",
            columns: {
                idColumnName: "id",
                vectorColumnName: "vector",
                contentColumnName: "content",
                metadataColumnName: "metadata",
            },
            // supported distance strategies: cosine (default), innerProduct, or euclidean
            distanceStrategy: "cosine",
        };
    }

    addDocuments = async (businessPhoneId, pageContents) => {
        const vectorStore = await PGVectorStore.initialize(this.embeddings, this.config);

        const documents = pageContents.map(pageContent => ({
            pageContent,
            metadata: { businessPhoneId },
        }));

        const ids = documents.map(() => uuidv4());

        await vectorStore.addDocuments(documents, { ids: ids });
    }
}
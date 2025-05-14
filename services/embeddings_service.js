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
                host: process.env.DB_HOST || "postgres",
                port: 5432,
                user: process.env.DB_USER || "postgres",
                password: process.env.DB_PASSWORD || "postgres",
                database: process.env.DB_NAME || "postgres",
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

        await vectorStore.addDocuments(documents, { ids });
    }
    
    listDocumentsByBusinessPhone = async (businessPhoneId) => {
        const vectorStore = await PGVectorStore.initialize(this.embeddings, this.config);
        
        // Usar SQL direto para buscar as informações sem precisar de embeddings
        const client = await vectorStore.pool.connect();
        
        try {
            const query = `
                SELECT id, content, metadata 
                FROM ${this.config.tableName} 
                WHERE metadata->>'businessPhoneId' = $1
                ORDER BY id DESC
            `;
            
            const result = await client.query(query, [businessPhoneId]);
            
            return result.rows.map(row => ({
                id: row.id,
                content: row.content,
                metadata: row.metadata
            }));
        } catch (error) {
            console.error("Error listing documents:", error);
            throw error;
        } finally {
            client.release();
        }
    }
}
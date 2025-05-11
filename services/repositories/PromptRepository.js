const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);
const error = (...args) => console.error(`[${new Date().toISOString()}]`, ...args);

export class PromptRepository {
    #pool;
    #tableExists = null;

    constructor(pool) {
        this.#pool = pool;
    }

    async checkTableExists() {
        try {
            if (this.#tableExists !== null) {
                return this.#tableExists;
            }

            const result = await this.#pool.query(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompts')"
            );
            
            this.#tableExists = result.rows[0].exists;
            
            if (!this.#tableExists) {
                log("Tabela 'prompts' não existe no banco de dados.");
            }
            
            return this.#tableExists;
        } catch (err) {
            error("Erro ao verificar se a tabela existe:", err);
            return false;
        }
    }

    async getPromptByBusinessPhone(businessPhoneId) {
        try {
            // Verificar se a tabela existe antes de tentar buscar dados
            const tableExists = await this.checkTableExists();
            if (!tableExists) {
                log("Tabela 'prompts' não existe. Usando prompt padrão.");
                return null;
            }

            const promptResult = await this.#pool.query(
                `SELECT content FROM prompts 
                 WHERE business_phone_id = $1 
                 AND active = true 
                 ORDER BY priority DESC LIMIT 1`,
                [businessPhoneId]
            );
            
            if (promptResult.rows.length > 0) {
                log("Prompt personalizado encontrado para:", businessPhoneId);
                return promptResult.rows[0].content;
            } else {
                log("Nenhum prompt personalizado encontrado para:", businessPhoneId);
                return null;
            }
        } catch (err) {
            error("Erro ao buscar prompts:", err);
            return null;
        }
    }
}

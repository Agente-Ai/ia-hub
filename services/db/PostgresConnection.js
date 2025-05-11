import pg from "pg";

const log = (...args) => console.log(`[${new Date().toISOString()}]`, ...args);
const error = (...args) => console.error(`[${new Date().toISOString()}]`, ...args);

const required = (name) => {
    const val = process.env[name];
    if (!val) throw new Error(`Missing required env var: ${name}`);
    return val;
};

export class PostgresConnection {
    static #instance = null;
    #pool = null;

    constructor() {
        if (PostgresConnection.#instance) {
            return PostgresConnection.#instance;
        }
        
        this.initPool();
        PostgresConnection.#instance = this;
    }

    initPool() {
        const config = {
            host: required("DB_HOST"),
            user: required("DB_USER"),
            password: required("DB_PASSWORD"),
            database: required("DB_NAME"),
            port: Number(process.env.DB_PORT || 5432),
            max: Number(process.env.DB_MAX_CONNECTIONS || 20),
            idleTimeoutMillis: 10000,
            connectionTimeoutMillis: 10000,
            ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : undefined,
        };

        log("Iniciando conexão com Postgres:", {
            host: config.host,
            user: config.user,
            database: config.database,
            port: config.port,
        });

        this.#pool = new pg.Pool(config);

        this.#pool.on("error", (err) => {
            error("Erro inesperado no pool Postgres:", err);
        });

        this.#pool.connect()
            .then((client) => {
                log("Conexão com Postgres estabelecida.");
                client.release();
            })
            .catch((err) => {
                error("Falha ao conectar com Postgres:", err.message);
                process.exit(1);
            });

        process.on("SIGINT", async () => {
            log("Encerrando pool Postgres...");
            await this.#pool.end();
            process.exit(0);
        });

        setInterval(() => {
            const stats = {
                total: this.#pool.totalCount,
                idle: this.#pool.idleCount,
                waiting: this.#pool.waitingCount,
            };
            log("Postgres pool stats:", stats);
        }, 60000);
    }

    getPool() {
        return this.#pool;
    }
}

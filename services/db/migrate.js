#!/usr/bin/env node

/**
 * Script para executar a migração SQL e criar a tabela de prompts
 */

import pg from 'pg';
import fs from 'fs';
import path from 'path';
import dotenv from "dotenv";
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Obter configurações do banco de dados
const dbConfig = {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    database: process.env.DB_NAME || 'ia_hub',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
};

// Função para executar a migração
async function runMigration() {
    console.log('Iniciando migração do banco de dados...');

    // Caminho do arquivo SQL de migração
    const sqlFilePath = path.join(__dirname, 'migrations', 'create_prompts_table.sql');
    console.log(`Lendo arquivo de migração: ${sqlFilePath}`);

    if (!fs.existsSync(sqlFilePath)) {
        console.error(`Arquivo de migração não encontrado: ${sqlFilePath}`);
        process.exit(1);
    }

    // Ler o conteúdo do arquivo SQL
    const sqlContent = fs.readFileSync(sqlFilePath, 'utf8');
    console.log('Arquivo SQL carregado com sucesso.');

    // Conectar ao banco de dados
    const client = new pg.Client(dbConfig);

    try {
        console.log('Conectando ao banco de dados...', {
            host: dbConfig.host,
            database: dbConfig.database,
            user: dbConfig.user,
            port: dbConfig.port,
        });
        await client.connect();
        console.log('Conexão estabelecida com sucesso.');

        console.log('Executando a migração...');
        // Executar o comando SQL
        await client.query(sqlContent);
        console.log('Migração executada com sucesso!');

        console.log('Verificando se a tabela foi criada...');
        const result = await client.query("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompts')");

        if (result.rows[0].exists) {
            console.log('✓ Tabela "prompts" criada com sucesso.');
        } else {
            console.error('✗ Falha ao criar a tabela "prompts".');
        }
    } catch (error) {
        console.error('Erro ao executar a migração:', error);
        process.exit(1);
    } finally {
        await client.end();
        console.log('Conexão com o banco de dados encerrada.');
    }
}

// Executar a migração
runMigration();

#!/bin/bash

# Script para executar a migração do banco de dados
# Este script executa a migração para criar a tabela de prompts

echo "Executando migração do banco de dados..."
node ./services/db/migrate.js

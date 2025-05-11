# Tabela de Prompts

## Descrição
O sistema utiliza prompts personalizados para cada empresa, armazenados na tabela `prompts` do banco de dados PostgreSQL.

## Estrutura da tabela
A tabela `prompts` tem a seguinte estrutura:

| Campo           | Tipo                    | Descrição                                |
|-----------------|-------------------------|-----------------------------------------|
| id              | SERIAL PRIMARY KEY      | Identificador único do prompt            |
| business_phone_id | VARCHAR(20) NOT NULL   | Número de telefone da empresa           |
| content         | TEXT NOT NULL           | Conteúdo do prompt personalizado        |
| active          | BOOLEAN DEFAULT TRUE    | Indica se o prompt está ativo           |
| priority        | INTEGER DEFAULT 0       | Prioridade (maior valor = maior prioridade) |
| created_at      | TIMESTAMP WITH TIME ZONE | Data de criação do registro            |
| updated_at      | TIMESTAMP WITH TIME ZONE | Data de atualização do registro        |

## Utilização
O sistema busca automaticamente um prompt personalizado para cada empresa com base no seu número de telefone (`business_phone_id`). Se existirem múltiplos prompts para a mesma empresa, o sistema utilizará o que tiver maior prioridade (campo `priority`) e que esteja ativo (campo `active` = TRUE).

## Criação da tabela no banco de dados
Para criar a tabela no banco de dados, execute o script de migração:

```bash
# Execute este comando na raiz do projeto
./run-migration.sh
```

## Exemplos de inserção de dados
Você pode inserir prompts personalizados para suas empresas usando comandos SQL como os exemplos abaixo:

```sql
-- Inserir um novo prompt para a empresa com telefone 553199999999
INSERT INTO prompts (business_phone_id, content, active, priority) VALUES
('553199999999', 'Você é o assistente da empresa XYZ. Responda de forma amigável e profissional.', TRUE, 10);

-- Inserir prompt com menor prioridade (será usado apenas se não houver um com prioridade maior)
INSERT INTO prompts (business_phone_id, content, active, priority) VALUES
('553199999999', 'Você é um assistente genérico da empresa XYZ.', TRUE, 5);

-- Desativar um prompt existente (se você conhece o ID do prompt)
UPDATE prompts SET active = FALSE WHERE id = 1;
```

## Solução de problemas
Se você encontrar o erro `relation "prompts" does not exist`, isso significa que a tabela ainda não foi criada no banco de dados. Execute o script de migração mencionado acima.

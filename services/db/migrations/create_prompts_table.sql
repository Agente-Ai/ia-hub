-- SQL para criar a tabela de prompts
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    business_phone_id VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para melhorar a busca por número de telefone
CREATE INDEX IF NOT EXISTS idx_prompts_business_phone_id ON prompts(business_phone_id);

-- Exemplo de inserção de dados
INSERT INTO prompts (business_phone_id, content, active, priority) VALUES
('553199999999', 'Você é o assistente da empresa XYZ. Responda de forma amigável e profissional, sempre priorizando informações sobre nossos produtos. Nossa missão é fornecer soluções de qualidade para nossos clientes.', TRUE, 10),
('553188888888', 'Você é o assistente da empresa ABC. Nosso foco é atendimento rápido e satisfatório. Sempre informe sobre promoções atuais e horários de funcionamento quando relevante. Somos especialistas em atendimento ao cliente.', TRUE, 10);

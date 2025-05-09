// swagger.js
import swaggerJsdoc from "swagger-jsdoc";

const options = {
    definition: {
        openapi: "3.0.0",
        info: {
            title: "API de Embeddings",
            version: "1.0.0",
            description: "Documentação da API para embeddings.",
        },
    },
    apis: ["./routes/*.js"], // Ajuste o path conforme a estrutura do projeto
};

export const swaggerSpec = swaggerJsdoc(options);

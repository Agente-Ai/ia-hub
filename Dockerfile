# Usa a imagem mais recente do Node.js
FROM node:latest

# Cria um diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos para o container
COPY package*.json ./
RUN npm install

COPY . .

# Expõe a porta 8080
EXPOSE 8080

# Comando para iniciar o servidor
CMD ["node", "index.js"]

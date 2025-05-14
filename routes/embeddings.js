import express from "express";
import { EmbeddingsService } from "../services/embeddings_service.js";

const router = express.Router();

/**
 * @swagger
 * tags:
 *   - name: Embeddings
 *     description: Operações relacionadas ao banco vetorial
 */

/**
 * @swagger
 * /api/embeddings/{businessPhoneId}:
 *   post:
 *     tags:
 *       - Embeddings
 *     summary: Adiciona documentos ao banco vetorial
 *     parameters:
 *       - in: path
 *         name: businessPhoneId
 *         required: true
 *         schema:
 *           type: string
 *         description: ID do telefone comercial
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: array
 *             items:
 *               type: string
 *             example:
 *               - "A pousada possui 4 acomodações"
 *               - "Café da manhã incluso na diária"
 *     responses:
 *       200:
 *         description: Documentos adicionados com sucesso
 *       500:
 *         description: Erro ao adicionar documentos
 */
router.post("/:businessPhoneId", async (req, res) => {
    const embeddingsService = new EmbeddingsService();
    const { businessPhoneId } = req.params;

    try {
        await embeddingsService.addDocuments(businessPhoneId, req.body);
        res.sendStatus(200);
    } catch (error) {
        console.error("Error adding documents to the vector database:", error);
        res.status(500).json({
            error: "Failed to add documents",
            details: error.message,
        });
    }
});

/**
 * @swagger
 * /api/embeddings/{businessPhoneId}:
 *   get:
 *     tags:
 *       - Embeddings
 *     summary: Lista documentos do banco vetorial por telefone comercial
 *     parameters:
 *       - in: path
 *         name: businessPhoneId
 *         required: true
 *         schema:
 *           type: string
 *         description: ID do telefone comercial
 *     responses:
 *       200:
 *         description: Lista de documentos
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 type: object
 *                 properties:
 *                   id:
 *                     type: string
 *                     description: ID único do documento
 *                   content:
 *                     type: string
 *                     description: Conteúdo do documento
 *                   metadata:
 *                     type: object
 *                     properties:
 *                       businessPhoneId:
 *                         type: string
 *                         description: ID do telefone comercial associado
 *       500:
 *         description: Erro ao listar documentos
 */
router.get("/:businessPhoneId", async (req, res) => {
    const embeddingsService = new EmbeddingsService();
    const { businessPhoneId } = req.params;

    try {
        const documents = await embeddingsService.listDocumentsByBusinessPhone(businessPhoneId);
        res.status(200).json(documents);
    } catch (error) {
        console.error("Error listing documents from the vector database:", error);
        res.status(500).json({
            error: "Failed to list documents",
            details: error.message,
        });
    }
});

export default router;

import express from "express";
import { EmbeddingsService } from "./services/embeddings_service.js";

const router = express.Router();

router.post("/:businessPhoneId/embeddings", async (req, res) => {
    const embeddingsService = new EmbeddingsService();

    const { businessPhoneId } = req.params;

    try {
        await embeddingsService.addDocuments(businessPhoneId, req.body)

        res.sendStatus(200);
    } catch (error) {
        console.error("Error adding documents to the vector database:", error);
        res.status(500).json({ error: "Failed to add documents", details: error.message });
    }
});

export default router;
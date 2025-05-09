import express from "express";
import { swaggerSpec } from "./swagger.js";
import swaggerUi from "swagger-ui-express";
import embeddingsRouter from "./routes/embeddings.js"; // ajuste o caminho

const router = express.Router();

router.use("/docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec));
router.use("/embeddings", embeddingsRouter);

export default router;
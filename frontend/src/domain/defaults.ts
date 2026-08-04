import type {
  ConversationDraftConfiguration,
  ModelConfiguration,
} from "./models"

export const createDefaultModelConfiguration = (): ModelConfiguration => ({
  llmModel: "llama3.2:3b",
  visionModel: "llama3.2-vision:11b",
  embedder: "llama3.2-embed:3b",
  pdfParser: "docling",
  vectorDatabase: "qdrant",
  ocrEngine: "paddleocr",
  contextCompressor: "auto",
  reranker: "llama3.2-reranker:3b",
})

export const createDefaultConversationDraft =
  (): ConversationDraftConfiguration => ({
    systemPrompt: "",
    modelConfiguration: createDefaultModelConfiguration(),
    sourceIds: [],
    temporary: false,
  })

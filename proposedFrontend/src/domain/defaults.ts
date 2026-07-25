import type {
  ConversationDraftConfiguration,
  ModelConfiguration,
} from "./models"

export const createDefaultModelConfiguration = (): ModelConfiguration => ({
  llmModel: "llama3.2:3b",
  visionModel: "llama3.2-vision:11b",
  embedder: "llama3.2-embed:3b",
  pdfParser: "llama3.2-pdf:3b",
  vectorDatabase: "llama3.2-vector:3b",
  ocrEngine: "llama3.2-ocr:3b",
  contextCompressor: "llama3.2-context:3b",
  reranker: "llama3.2-reranker:3b",
})

export const createDefaultConversationDraft =
  (): ConversationDraftConfiguration => ({
    systemPrompt: "",
    modelConfiguration: createDefaultModelConfiguration(),
    sourceIds: [],
    temporary: false,
  })

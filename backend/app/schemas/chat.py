from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatHistoryMessage(BaseModel):
    """One prior message supplied as context for the current chat."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class ConversationSettings(BaseModel):
    """Per-conversation AI component settings supplied by the browser."""

    model_config = ConfigDict(extra="ignore")

    llmModel: str | None = Field(default=None, max_length=100)
    embedderModel: str | None = Field(default=None, max_length=100)
    ocrEngine: str | None = Field(default=None, max_length=100)
    pdfParser: str | None = Field(default=None, max_length=100)
    chunker: str | None = Field(default=None, max_length=100)
    vectorDatabase: str | None = Field(default=None, max_length=100)
    ragPipeline: str | None = Field(default=None, max_length=100)
    reranker: str | None = Field(default=None, max_length=100)
    contextCompressor: str | None = Field(default=None, max_length=100)
    visionModel: str | None = Field(default=None, max_length=100)


class RagOptions(BaseModel):
    """Optional retrieval controls supplied with a chat request."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    topK: int = Field(default=5, ge=1, le=20)
    candidateK: int = Field(default=20, ge=1, le=50)
    documentIds: list[str] = Field(default_factory=list, max_length=50)
    includeSources: bool = True


class ChatImageAttachment(BaseModel):
    """One image supplied for a local vision-model chat request."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="image", min_length=1, max_length=255)
    mimeType: Literal["image/png", "image/jpeg", "image/webp"] = "image/png"
    data: str = Field(min_length=1, max_length=8_000_000)


class ChatRequest(BaseModel):
    """Input accepted by the chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    conversationId: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10_000)
    conversationSettings: ConversationSettings | None = None
    ragOptions: RagOptions | None = None
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=30,
    )
    images: list[ChatImageAttachment] = Field(
        default_factory=list,
        max_length=4,
    )


class ChatSource(BaseModel):
    """One retrieved document chunk used as chat context."""

    sourceNumber: int
    documentId: str
    documentName: str
    chunkId: str
    chunkIndex: int
    score: float
    vectorScore: float
    rerankScore: float | None = None
    finalRank: int
    textPreview: str
    collectionId: str | None = None


class ChatCompressionStats(BaseModel):
    """Metadata describing optional prompt compression."""

    originalCharEstimate: int = 0
    compressedCharEstimate: int = 0
    originalTokenEstimate: int = 0
    compressedTokenEstimate: int = 0
    messagesTrimmed: int = 0
    contextTrimmed: int = 0
    summaryGenerated: bool = False


class ChatResponse(BaseModel):
    """Output returned by the chat endpoint."""

    model: str
    answer: str
    ragUsed: bool = False
    ragWarnings: list[str] = Field(default_factory=list)
    rerankingUsed: bool = False
    rerankerModel: str | None = None
    rerankWarnings: list[str] = Field(default_factory=list)
    compressionUsed: bool = False
    compressorMode: str = "none"
    compressionWarnings: list[str] = Field(default_factory=list)
    compressionStats: ChatCompressionStats = Field(
        default_factory=ChatCompressionStats
    )
    visionUsed: bool = False
    visionModel: str | None = None
    visionWarnings: list[str] = Field(default_factory=list)
    sources: list[ChatSource] = Field(default_factory=list)

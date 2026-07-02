from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import ConversationSettings


class ProcessDocumentRequest(BaseModel):
    """Request body for processing a staged conversation document."""

    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=100)
    conversationSettings: ConversationSettings | None = None


class IndexDocumentRequest(BaseModel):
    """Request body for embedding and indexing one processed document."""

    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=100)
    conversationSettings: ConversationSettings | None = None


class SearchDocumentsRequest(BaseModel):
    """Request body for retrieval-only search over indexed documents."""

    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=2000)
    conversationSettings: ConversationSettings | None = None
    documentIds: list[str] = Field(default_factory=list, max_length=50)
    topK: int = Field(default=5, ge=1, le=20)

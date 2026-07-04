from pydantic import BaseModel, Field

from app.schemas.chat import ConversationSettings


class IndexLocalRepositoryRequest(BaseModel):
    """Input accepted by the local repository indexing endpoint."""

    path: str = Field(min_length=1)


class IndexLocalRepositoryResponse(BaseModel):
    """Summary returned after a local repository is indexed."""

    repo_name: str
    indexed_files: int
    indexed_chunks: int
    freshness: dict[str, object] | None = None
    warnings: list[str] = Field(default_factory=list)


class AskRepositoryRequest(BaseModel):
    """Input accepted by the repository question endpoint."""

    repo_name: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=10_000)


class AskRepositoryResponse(BaseModel):
    """Answer and source paths returned by repository RAG."""

    answer: str
    sources: list[str]
    warnings: list[str] = Field(default_factory=list)
    freshness: dict[str, object] | None = None


class IndexRepositoryVectorRequest(BaseModel):
    """Input accepted by opt-in repository vector indexing."""

    path: str = Field(min_length=1)
    conversationId: str = Field(min_length=1, max_length=100)
    conversationSettings: ConversationSettings | None = None


class IndexRepositoryVectorResponse(BaseModel):
    """Summary returned after repository chunks are embedded."""

    repo_name: str
    indexed_files: int
    indexed_chunks: int
    embedded_chunks: int
    conversationId: str
    collectionId: str
    collection: dict[str, object]
    embedderModel: str
    vectorDatabase: str
    freshness: dict[str, object]
    warnings: list[str] = Field(default_factory=list)


class SearchRepositoryVectorRequest(BaseModel):
    """Input accepted by opt-in repository vector search."""

    conversationId: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=10_000)
    repoName: str | None = Field(default=None, min_length=1, max_length=255)
    topK: int = Field(default=5, ge=1, le=20)
    conversationSettings: ConversationSettings | None = None

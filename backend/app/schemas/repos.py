from pydantic import BaseModel, Field


class IndexLocalRepositoryRequest(BaseModel):
    """Input accepted by the local repository indexing endpoint."""

    path: str = Field(min_length=1)


class IndexLocalRepositoryResponse(BaseModel):
    """Summary returned after a local repository is indexed."""

    repo_name: str
    indexed_files: int
    indexed_chunks: int


class AskRepositoryRequest(BaseModel):
    """Input accepted by the repository question endpoint."""

    repo_name: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=10_000)


class AskRepositoryResponse(BaseModel):
    """Answer and source paths returned by repository RAG."""

    answer: str
    sources: list[str]

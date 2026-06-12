from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Input accepted by the planned chat endpoint."""

    model: str = Field(default="qwen3:4b", min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """Output returned by the planned chat endpoint."""

    answer: str

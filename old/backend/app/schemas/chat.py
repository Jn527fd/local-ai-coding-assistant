from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatHistoryMessage(BaseModel):
    """One prior message supplied as context for the current chat."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class ChatRequest(BaseModel):
    """Input accepted by the chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10_000)
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=30,
    )


class ChatResponse(BaseModel):
    """Output returned by the chat endpoint."""

    model: str
    answer: str

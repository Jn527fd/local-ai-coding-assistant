from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal[
    "preference",
    "decision",
    "constraint",
    "task",
    "project_fact",
]


class MemoryRecord(BaseModel):
    """One durable conversational memory stored outside document/repo RAG."""

    id: str
    workspaceId: str
    conversationId: str | None = None
    text: str
    type: MemoryType
    importance: float = Field(ge=0.0, le=1.0)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sourceMessageId: str | None = None
    sourceRole: str | None = None
    sourceHash: str
    score: float | None = None


class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspaceId: str = Field(default="default", min_length=1, max_length=120)
    conversationId: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=1, max_length=2_000)
    type: MemoryType
    importance: float = Field(default=0.6, ge=0.0, le=1.0)
    sourceMessageId: str | None = Field(default=None, max_length=160)
    sourceRole: str | None = Field(default=None, max_length=40)
    embedderModel: str = Field(min_length=1, max_length=100)


class MemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspaceId: str = Field(default="default", min_length=1, max_length=120)
    conversationId: str | None = Field(default=None, max_length=100)
    query: str = Field(min_length=1, max_length=2_000)
    embedderModel: str = Field(min_length=1, max_length=100)
    topK: int = Field(default=5, ge=1, le=20)
    memoryTypes: list[MemoryType] = Field(default_factory=list, max_length=10)
    minImportance: float = Field(default=0.0, ge=0.0, le=1.0)
    includeWorkspaceWide: bool = True


class MemoryListResponse(BaseModel):
    memories: list[MemoryRecord]
    warnings: list[str] = Field(default_factory=list)


class MemoryDeleteResponse(BaseModel):
    deleted: bool
    memoryId: str


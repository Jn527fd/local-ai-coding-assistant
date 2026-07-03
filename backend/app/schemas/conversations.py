from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import ConversationSettings


class ConversationRecord(BaseModel):
    """One persisted browser conversation record."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=100)
    title: str = Field(default="Untitled thread", min_length=1, max_length=200)
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    settings: ConversationSettings = Field(default_factory=ConversationSettings)
    metadata: dict[str, Any] = Field(default_factory=dict)
    attachmentReferences: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=200,
    )
    createdAt: str | None = Field(default=None, max_length=80)
    updatedAt: str | None = Field(default=None, max_length=80)


class ConversationListResponse(BaseModel):
    persistence: str = "backend"
    conversations: list[ConversationRecord] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    conversation: ConversationRecord


class ConversationDeleteResponse(BaseModel):
    deleted: bool
    conversationId: str


class ConversationImportRequest(BaseModel):
    conversations: list[ConversationRecord] = Field(
        default_factory=list,
        max_length=100,
    )
    replace: bool = False


class ConversationImportResponse(BaseModel):
    imported: int
    conversations: list[ConversationRecord] = Field(default_factory=list)


class ConversationExportResponse(BaseModel):
    username: str
    exportedAt: str
    conversations: list[ConversationRecord] = Field(default_factory=list)

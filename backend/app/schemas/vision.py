from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class VisionEvidenceArtifact(BaseModel):
    """Structured evidence extracted from an uploaded image."""

    id: str
    workspaceId: str = "default"
    conversationId: str
    messageId: str
    imageId: str
    imageName: str
    mimeType: str
    visionModel: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "succeeded"
    visibleText: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    filePaths: list[str] = Field(default_factory=list)
    code: list[str] = Field(default_factory=list)
    uiElements: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

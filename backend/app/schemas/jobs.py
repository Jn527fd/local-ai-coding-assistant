from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JobState = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancel_requested",
    "cancelled",
]


class JobRecord(BaseModel):
    """Serializable local background job state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    state: JobState
    progress: int = Field(default=0, ge=0, le=100)
    message: str | None = None
    targetType: str | None = None
    targetId: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    cancelRequested: bool = False
    createdAt: str
    updatedAt: str
    startedAt: str | None = None
    finishedAt: str | None = None


class JobResponse(BaseModel):
    job: JobRecord


class JobListResponse(BaseModel):
    jobs: list[JobRecord]

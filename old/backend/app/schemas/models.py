from typing import Literal

from pydantic import BaseModel, Field


class SupportedModel(BaseModel):
    name: str
    label: str
    parameters_billion: float
    parameter_size: str
    size_bytes: int
    size_display: str
    family: str | None = None
    quantization_level: str | None = None


class ModelSwitchRequest(BaseModel):
    model: str = Field(min_length=1, max_length=100)


class ModelSwitchResponse(BaseModel):
    accepted: bool
    model: str


class ModelStatusResponse(BaseModel):
    active_model: str
    supported_models: list[SupportedModel]
    installed_models: list[str]
    excluded_model_count: int
    max_parameters_billion: float
    ollama_connected: bool
    switching: bool
    target_model: str | None = None
    phase: Literal[
        "idle",
        "activating",
        "complete",
        "error",
    ]
    progress: int | None = None
    message: str
    error: str | None = None
    warning: str | None = None

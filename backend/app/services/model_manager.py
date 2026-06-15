import asyncio
from dataclasses import dataclass
from typing import Final

from app.services.local_settings_service import (
    LocalSettingsError,
    LocalSettingsService,
)
from app.services.ollama_service import (
    OllamaService,
    OllamaServiceError,
)


@dataclass(frozen=True)
class ModelDefinition:
    name: str
    label: str
    parameters_billion: float
    approximate_download: str


SUPPORTED_MODELS: Final[tuple[ModelDefinition, ...]] = (
    ModelDefinition("qwen3:4b", "Qwen 3 4B", 4.0, "2.5 GB"),
    ModelDefinition(
        "qwen2.5-coder:3b",
        "Qwen 2.5 Coder 3B",
        3.0,
        "1.9 GB",
    ),
    ModelDefinition(
        "qwen2.5-coder:7b",
        "Qwen 2.5 Coder 7B",
        7.0,
        "4.7 GB",
    ),
    ModelDefinition("llama3.2:1b", "Llama 3.2 1B", 1.0, "1.3 GB"),
    ModelDefinition("llama3.2:3b", "Llama 3.2 3B", 3.0, "2.0 GB"),
)
SUPPORTED_MODEL_NAMES: Final[frozenset[str]] = frozenset(
    model.name for model in SUPPORTED_MODELS
)


class UnsupportedModelError(Exception):
    """Raised when a model is outside the approved 7B-or-smaller catalog."""


class ModelSwitchInProgressError(Exception):
    """Raised when another model switch is already running."""


class ModelManager:
    """Coordinate one safe Ollama model switch at a time."""

    def __init__(
        self,
        ollama_service: OllamaService,
        local_settings: LocalSettingsService,
        default_model: str,
        pull_timeout_seconds: float,
        delete_previous_model: bool,
    ) -> None:
        if default_model not in SUPPORTED_MODEL_NAMES:
            raise ValueError("The configured default model is not supported.")

        self.ollama_service = ollama_service
        self.local_settings = local_settings
        self.default_model = default_model
        self.pull_timeout_seconds = pull_timeout_seconds
        self.delete_previous_model = delete_previous_model
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._target_model: str | None = None
        self._phase = "idle"
        self._progress: int | None = None
        self._message = "Ready"
        self._error: str | None = None
        self._warning: str | None = None

    @property
    def active_model(self) -> str:
        model = self.local_settings.get_active_model(self.default_model)
        return model if model in SUPPORTED_MODEL_NAMES else self.default_model

    @property
    def is_switching(self) -> bool:
        return self._task is not None and not self._task.done()

    def validate_model(self, model: str) -> None:
        if model not in SUPPORTED_MODEL_NAMES:
            raise UnsupportedModelError(
                "Unsupported model. Select a listed model with 7B parameters "
                "or fewer."
            )

    async def start_switch(self, model: str) -> None:
        self.validate_model(model)
        if self._task is not None and not self._task.done():
            raise ModelSwitchInProgressError(
                "A model switch is already in progress."
            )

        self._target_model = model
        self._phase = "unloading"
        self._progress = 0
        self._message = f"Preparing to switch to {model}."
        self._error = None
        self._warning = None
        self._task = asyncio.create_task(self._switch(model))

    async def status(self, refresh_installed: bool = True) -> dict[str, object]:
        installed_models: list[str] = []
        connected = False
        if refresh_installed:
            try:
                installed_models = (
                    await self.ollama_service.list_installed_models()
                )
                connected = True
            except OllamaServiceError:
                connected = False

        switching = self.is_switching
        return {
            "active_model": self.active_model,
            "supported_models": [
                {
                    "name": model.name,
                    "label": model.label,
                    "parameters_billion": model.parameters_billion,
                    "approximate_download": model.approximate_download,
                }
                for model in SUPPORTED_MODELS
            ],
            "installed_models": installed_models,
            "ollama_connected": connected,
            "switching": switching,
            "target_model": self._target_model if switching else None,
            "phase": self._phase,
            "progress": self._progress,
            "message": self._message,
            "error": self._error,
            "warning": self._warning,
        }

    async def wait_for_switch(self) -> None:
        """Wait for the current switch task, primarily for orderly callers."""

        if self._task is not None:
            await self._task

    async def close(self) -> None:
        """Cancel an unfinished model operation during application shutdown."""

        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _switch(self, target_model: str) -> None:
        async with self._lock:
            previous_model = self.active_model
            try:
                if previous_model == target_model:
                    installed = (
                        await self.ollama_service.list_installed_models()
                    )
                    if target_model in installed:
                        self._complete(
                            f"{target_model} is already active and installed."
                        )
                        return

                if previous_model:
                    self._phase = "unloading"
                    self._message = f"Unloading {previous_model} from memory."
                    try:
                        await self.ollama_service.unload_model(previous_model)
                    except OllamaServiceError:
                        # Pulling can still recover when the previous model is
                        # absent, so this is not fatal.
                        self._warning = (
                            f"Could not unload {previous_model}; continuing."
                        )

                self._phase = "downloading"
                self._message = f"Downloading {target_model}."
                self._progress = 0
                await self.ollama_service.pull_model(
                    target_model,
                    self._update_download_progress,
                    self.pull_timeout_seconds,
                )

                self._phase = "activating"
                self._progress = 100
                self._message = f"Setting {target_model} as active."
                self.local_settings.set_active_model(target_model)

                if (
                    self.delete_previous_model
                    and previous_model
                    and previous_model != target_model
                ):
                    self._phase = "cleaning"
                    self._message = (
                        f"Removing unused model files for {previous_model}."
                    )
                    try:
                        await self.ollama_service.delete_model(previous_model)
                    except OllamaServiceError as exc:
                        self._warning = (
                            f"{target_model} is active, but the previous model "
                            f"could not be deleted: {exc}"
                        )

                self._complete(f"{target_model} is installed and active.")
            except (
                LocalSettingsError,
                OllamaServiceError,
                OSError,
                ValueError,
            ) as exc:
                self._phase = "error"
                self._progress = None
                self._message = "Model switch failed."
                self._error = str(exc)

    def _update_download_progress(
        self,
        progress: int | None,
        message: str,
    ) -> None:
        self._progress = progress
        self._message = message

    def _complete(self, message: str) -> None:
        self._phase = "complete"
        self._progress = 100
        self._message = message
        self._error = None

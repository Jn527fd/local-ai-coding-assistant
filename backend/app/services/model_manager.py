import asyncio
from dataclasses import dataclass

from app.services.local_settings_service import (
    LocalSettingsError,
    LocalSettingsService,
)
from app.services.ollama_service import (
    InstalledOllamaModel,
    OllamaService,
    OllamaServiceError,
)


@dataclass(frozen=True)
class ModelDefinition:
    name: str
    label: str
    parameters_billion: float | None
    parameter_size: str
    size_bytes: int
    size_display: str
    family: str | None
    quantization_level: str | None


class UnsupportedModelError(Exception):
    """Raised when a model is absent from the local Ollama inventory."""


class ModelSwitchInProgressError(Exception):
    """Raised when another model switch is already running."""


class ModelManager:
    """Coordinate one safe Ollama model switch at a time."""

    def __init__(
        self,
        ollama_service: OllamaService,
        local_settings: LocalSettingsService,
        default_model: str,
    ) -> None:
        self.ollama_service = ollama_service
        self.local_settings = local_settings
        self.default_model = default_model
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
        return self.local_settings.get_active_model(self.default_model)

    @property
    def is_switching(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start_switch(self, model: str) -> None:
        if self._task is not None and not self._task.done():
            raise ModelSwitchInProgressError(
                "A model switch is already in progress."
            )

        installed_models = await self.ollama_service.list_installed_models()
        installed_model = next(
            (item for item in installed_models if item.name == model),
            None,
        )
        self._validate_installed_model(model, installed_model)

        self._target_model = model
        self._phase = "activating"
        self._progress = 0
        self._message = f"Setting {model} as active."
        self._error = None
        self._warning = None
        self._task = asyncio.create_task(self._switch(model))

    async def status(self, refresh_installed: bool = True) -> dict[str, object]:
        installed_models: list[InstalledOllamaModel] = []
        supported_models: list[ModelDefinition] = []
        connected = False
        if refresh_installed:
            try:
                installed_models = (
                    await self.ollama_service.list_installed_models()
                )
                supported_models = self._supported_models(installed_models)
                connected = True
            except OllamaServiceError:
                connected = False

        switching = self.is_switching
        active_model = self.active_model
        supported_names = {model.name for model in supported_models}
        if supported_models and active_model not in supported_names:
            fallback = next(
                (
                    model.name
                    for model in supported_models
                    if model.name == self.default_model
                ),
                supported_models[0].name,
            )
            try:
                self.local_settings.set_active_model(fallback)
                active_model = fallback
            except LocalSettingsError as exc:
                self._warning = str(exc)

        return {
            "active_model": active_model,
            "supported_models": [
                {
                    "name": model.name,
                    "label": model.label,
                    "parameters_billion": model.parameters_billion,
                    "parameter_size": model.parameter_size,
                    "size_bytes": model.size_bytes,
                    "size_display": model.size_display,
                    "family": model.family,
                    "quantization_level": model.quantization_level,
                }
                for model in supported_models
            ],
            "installed_models": [model.name for model in installed_models],
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
            try:
                self._progress = 100
                self._message = f"Setting {target_model} as active."
                self.local_settings.set_active_model(target_model)
                self._complete(
                    f"{target_model} is installed locally and is now active."
                )
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

    def _complete(self, message: str) -> None:
        self._phase = "complete"
        self._progress = 100
        self._message = message
        self._error = None

    def _supported_models(
        self,
        installed_models: list[InstalledOllamaModel],
    ) -> list[ModelDefinition]:
        models = [
            self._model_definition(model)
            for model in installed_models
        ]
        return sorted(models, key=lambda model: model.name.lower())

    def _validate_installed_model(
        self,
        name: str,
        model: InstalledOllamaModel | None,
    ) -> None:
        if model is None:
            raise UnsupportedModelError(
                f"{name} is not installed locally. Pull it with Ollama, then "
                "refresh the model list."
            )

    @staticmethod
    def _model_definition(model: InstalledOllamaModel) -> ModelDefinition:
        return ModelDefinition(
            name=model.name,
            label=model.name,
            parameters_billion=model.parameters_billion,
            parameter_size=model.parameter_size or "unknown size",
            size_bytes=model.size_bytes,
            size_display=ModelManager._format_size(model.size_bytes),
            family=model.family,
            quantization_level=model.quantization_level,
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        gibibytes = size_bytes / (1024**3)
        if gibibytes >= 1:
            return f"{gibibytes:.1f} GiB"
        mebibytes = size_bytes / (1024**2)
        return f"{mebibytes:.0f} MiB"

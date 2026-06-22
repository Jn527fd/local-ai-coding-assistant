from dataclasses import dataclass
import logging
import re
from time import monotonic
from typing import Any

import httpx

logger = logging.getLogger(__name__)
PARAMETER_SIZE_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([KMBT])\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InstalledOllamaModel:
    """Metadata for one model reported by Ollama's local model inventory."""

    name: str
    size_bytes: int
    parameter_size: str
    parameters_billion: float | None
    family: str | None
    quantization_level: str | None


def parse_parameter_size_billions(value: str) -> float | None:
    """Convert Ollama parameter sizes such as 7B or 500M into billions."""

    match = PARAMETER_SIZE_PATTERN.fullmatch(value)
    if match is None:
        return None

    amount = float(match.group(1))
    multiplier = {
        "K": 0.000001,
        "M": 0.001,
        "B": 1.0,
        "T": 1000.0,
    }[match.group(2).upper()]
    return amount * multiplier


class OllamaServiceError(Exception):
    """Base error raised by the Ollama service."""


class OllamaUnavailableError(OllamaServiceError):
    """Raised when the backend cannot connect to Ollama."""


class OllamaTimeoutError(OllamaServiceError):
    """Raised when Ollama does not respond before the configured timeout."""


class OllamaResponseError(OllamaServiceError):
    """Raised when Ollama returns an error or an invalid response."""


class OllamaService:
    """Client for Ollama's local generation API."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        num_predict: int = 768,
        think: bool = False,
        keep_alive: str = "10m",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.num_predict = num_predict
        self.think = think
        self.keep_alive = keep_alive

    async def generate(self, model: str, prompt: str) -> str:
        """Generate a complete non-streaming response from Ollama."""

        started_at = monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "think": self.think,
                        "keep_alive": self.keep_alive,
                        "options": {
                            "num_predict": self.num_predict,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning(
                "Ollama generation timed out model=%s prompt_chars=%d "
                "elapsed_seconds=%.2f",
                model,
                len(prompt),
                monotonic() - started_at,
            )
            raise OllamaTimeoutError(
                f"Ollama did not respond within {self.timeout_seconds:g} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Unable to connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = self._error_detail(exc.response)
            raise OllamaResponseError(
                f"Ollama returned HTTP {exc.response.status_code}: {detail}"
            ) from exc

        try:
            data: Any = response.json()
        except ValueError as exc:
            raise OllamaResponseError(
                "Ollama returned a response that was not valid JSON."
            ) from exc

        answer = data.get("response") if isinstance(data, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            thinking = data.get("thinking") if isinstance(data, dict) else None
            if isinstance(thinking, str) and thinking.strip():
                raise OllamaResponseError(
                    "Ollama used the generation budget for thinking but did "
                    "not return a final answer. Disable OLLAMA_THINK or "
                    "increase OLLAMA_NUM_PREDICT."
                )
            raise OllamaResponseError(
                "Ollama returned a response without generated text."
            )

        logger.info(
            "Ollama generation completed model=%s prompt_chars=%d "
            "prompt_tokens=%s output_tokens=%s elapsed_seconds=%.2f",
            model,
            len(prompt),
            data.get("prompt_eval_count"),
            data.get("eval_count"),
            monotonic() - started_at,
        )
        return answer.strip()

    async def is_available(self) -> bool:
        """Return whether the local Ollama API can be reached."""

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return True
        except (httpx.HTTPError, ValueError):
            return False

    async def list_installed_models(self) -> list[InstalledOllamaModel]:
        """Return installed models and their local Ollama metadata."""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                "Ollama timed out while listing installed models."
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Unable to connect to Ollama at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaResponseError(
                f"Ollama returned HTTP {exc.response.status_code} while "
                "listing models."
            ) from exc

        try:
            data: Any = response.json()
            models = data.get("models") if isinstance(data, dict) else None
        except ValueError as exc:
            raise OllamaResponseError(
                "Ollama returned invalid JSON while listing models."
            ) from exc

        if not isinstance(models, list):
            raise OllamaResponseError(
                "Ollama returned an invalid installed-model list."
            )

        installed_models: list[InstalledOllamaModel] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            details = item.get("details")
            if not isinstance(name, str) or not isinstance(details, dict):
                continue

            parameter_size = details.get("parameter_size")
            if not isinstance(parameter_size, str):
                parameter_size = ""
            size_bytes = item.get("size")
            family = details.get("family")
            quantization = details.get("quantization_level")
            installed_models.append(
                InstalledOllamaModel(
                    name=name,
                    size_bytes=(
                        size_bytes
                        if isinstance(size_bytes, int) and size_bytes >= 0
                        else 0
                    ),
                    parameter_size=parameter_size,
                    parameters_billion=parse_parameter_size_billions(
                        parameter_size
                    ),
                    family=family if isinstance(family, str) else None,
                    quantization_level=(
                        quantization
                        if isinstance(quantization, str)
                        else None
                    ),
                )
            )
        return installed_models

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """Extract a concise error message from an Ollama response."""

        try:
            data: Any = response.json()
        except ValueError:
            return response.text.strip() or "Unknown Ollama error."

        if isinstance(data, dict) and isinstance(data.get("error"), str):
            return data["error"]

        return "Unknown Ollama error."

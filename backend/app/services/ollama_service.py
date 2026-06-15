from collections.abc import Callable
import json
from typing import Any

import httpx


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

    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def generate(self, model: str, prompt: str) -> str:
        """Generate a complete non-streaming response from Ollama."""

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
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
            raise OllamaResponseError(
                "Ollama returned a response without generated text."
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

    async def list_installed_models(self) -> list[str]:
        """Return installed Ollama model names."""

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

        names: list[str] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            if isinstance(name, str):
                names.append(name)
        return names

    async def unload_model(self, model: str) -> None:
        """Unload a model from memory without removing its files."""

        await self._request(
            "POST",
            "/api/generate",
            json_body={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
        )

    async def delete_model(self, model: str) -> None:
        """Delete an installed model through Ollama."""

        await self._request(
            "DELETE",
            "/api/delete",
            json_body={"model": model},
        )

    async def pull_model(
        self,
        model: str,
        progress_callback: Callable[[int | None, str], None],
        timeout_seconds: float,
    ) -> None:
        """Pull a model and report streamed progress updates."""

        timeout = httpx.Timeout(timeout_seconds, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"model": model, "stream": True},
                ) as response:
                    if response.is_error:
                        await response.aread()
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            update: Any = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise OllamaResponseError(
                                "Ollama returned invalid pull progress JSON."
                            ) from exc

                        if not isinstance(update, dict):
                            continue
                        error = update.get("error")
                        if isinstance(error, str) and error:
                            raise OllamaResponseError(error)

                        status_text = update.get("status")
                        status_message = (
                            status_text
                            if isinstance(status_text, str)
                            else "Downloading model"
                        )
                        completed = update.get("completed")
                        total = update.get("total")
                        percent: int | None = None
                        if (
                            isinstance(completed, int)
                            and isinstance(total, int)
                            and total > 0
                        ):
                            percent = min(
                                100,
                                max(0, round((completed / total) * 100)),
                            )
                        progress_callback(percent, status_message)
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Model download exceeded {timeout_seconds:g} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Unable to connect to Ollama at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = self._error_detail(exc.response)
            raise OllamaResponseError(
                f"Ollama returned HTTP {exc.response.status_code}: {detail}"
            ) from exc

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any],
    ) -> None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    json=json_body,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama did not respond within {self.timeout_seconds:g} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Unable to connect to Ollama at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = self._error_detail(exc.response)
            raise OllamaResponseError(
                f"Ollama returned HTTP {exc.response.status_code}: {detail}"
            ) from exc

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

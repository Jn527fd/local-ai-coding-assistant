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

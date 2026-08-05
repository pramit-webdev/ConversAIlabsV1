"""API clients for OpenRouter (chat) and the embedding provider (NVIDIA/Groq/OpenRouter).

All providers expose an OpenAI-compatible embeddings endpoint, so a single
client class with per-provider configuration covers everything.
"""
from __future__ import annotations

import time

import httpx

from .config import settings

TIMEOUT = 60.0
FREE_MODEL_NOT_FOUND_STATUSES = {400, 404, 402, 429, 502}


class OpenRouterError(Exception):
    """Raised when the model API cannot serve a request."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class ApiClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        key_env_var: str,
        model: str | None = None,
    ) -> None:
        if not api_key:
            raise OpenRouterError(
                f"{key_env_var} is not set. Create a free key and add it to your .env file."
            )
        self._model = model
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Embeddings
    # ------------------------------------------------------------------ #
    def embed(self, texts: list[str], *, input_type: str = "passage") -> list[list[float]]:
        """Embed a batch of texts. Returns a list of vectors.

        Some providers (NVIDIA Nemotron) honour an `input_type` passage/query
        hint; others reject it. On a bad request we retry without it, and we
        back off on 429s (free-tier rate limits) and pace batches so bulk
        ingestion stays within the provider's RPM budget.
        """
        if not texts:
            return []
        payload = {
            "model": self._model,
            "input": texts,
            "encoding_format": "float",
        }
        vectors: list[list[float]] = []
        for i in range(0, len(texts), settings.max_embed_batch):
            batch = texts[i : i + settings.max_embed_batch]
            data = self._embed_batch(payload, batch, input_type)
            vectors.extend(item["embedding"] for item in data["data"])
            time.sleep(1.6)  # ~37 req/min < 40 RPM free-tier ceiling
        return vectors

    def _embed_batch(self, payload: dict, batch: list[str], input_type: str) -> dict:
        sent_input_type = True
        for attempt in range(6):
            body = {**payload, "input": batch}
            if sent_input_type:
                body["input_type"] = input_type
            try:
                return self._post("/embeddings", body)
            except OpenRouterError as exc:
                if exc.status in {429, 500, 502, 503} and attempt < 5:
                    # rate limit or transient provider hiccup: back off and retry
                    time.sleep(2**attempt * 1.5)
                    continue
                if exc.status in {400, 422} and sent_input_type:
                    sent_input_type = False  # provider rejects input_type; retry without it
                    continue
                raise

    # ------------------------------------------------------------------ #
    # Chat (OpenRouter only)
    # ------------------------------------------------------------------ #
    def chat(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        """Single-turn completion. Tries the configured model, then fallbacks."""
        models = [settings.llm_model, *settings.llm_fallback_models]
        last_error: OpenRouterError | None = None
        for model in models:
            try:
                data = self._post(
                    "/chat/completions",
                    {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    },
                )
                content = data["choices"][0]["message"].get("content")
                if content and content.strip():
                    return content.strip()
                raise OpenRouterError(f"Model {model!r} returned an empty response", status=502)
            except OpenRouterError as exc:
                last_error = exc
                if exc.status not in FREE_MODEL_NOT_FOUND_STATUSES:
                    raise
                print(f"[llm] model {model!r} unavailable ({exc.status}), trying next")
        raise OpenRouterError(f"All configured models failed: {last_error}")

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _post(self, path: str, json_body: dict) -> dict:
        response = self._client.post(path, json=json_body)
        if response.status_code >= 400:
            raise OpenRouterError(
                f"API {path} failed ({response.status_code}): {response.text[:500]}",
                status=response.status_code,
            )
        return response.json()


def build_embedder() -> ApiClient:
    """Client for the configured embedding provider."""
    return ApiClient(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        key_env_var="EMBEDDING_API_KEY",
        model=settings.embedding_model,
    )


def build_llm() -> ApiClient:
    """Client for OpenRouter chat completions."""
    return ApiClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        key_env_var="OPENROUTER_API_KEY",
    )

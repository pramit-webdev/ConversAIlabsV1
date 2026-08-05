"""API clients for OpenRouter (chat) and the embedding provider (NVIDIA/Groq/OpenRouter).

All providers expose an OpenAI-compatible embeddings endpoint, so a single
client class with per-provider configuration covers everything.
"""
from __future__ import annotations

import json
import time
from typing import Iterator

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
                if exc.status is not None and exc.status not in FREE_MODEL_NOT_FOUND_STATUSES:
                    raise
                print(f"[llm] model {model!r} unavailable ({exc.status}), trying next")
        return _chat_with_nvidia_fallback(system, user, max_tokens=max_tokens, last_error=last_error)

    def chat_stream(self, system: str, user: str, *, max_tokens: int = 1024) -> "OpenAIStream":
        """Streaming completion. Falls back across configured models until the
        first token arrives; a mid-stream failure is raised to the caller."""
        models = [settings.llm_model, *settings.llm_fallback_models]
        last_error: OpenRouterError | None = None
        for model in models:
            stream = OpenAIStream(self._client, model, system, user, max_tokens=max_tokens)
            try:
                # Fail fast on non-2xx before yielding anything so fallbacks work
                stream.open()
            except OpenRouterError as exc:
                last_error = exc
                if exc.status is not None and exc.status not in FREE_MODEL_NOT_FOUND_STATUSES:
                    raise
                print(f"[llm] model {model!r} unavailable ({exc.status}), trying next")
                continue
            return stream
        return _stream_with_nvidia_fallback(system, user, max_tokens=max_tokens, last_error=last_error)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _post(self, path: str, json_body: dict) -> dict:
        try:
            response = self._client.post(path, json=json_body)
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"API {path} failed (network error): {exc}", status=None) from exc
        if response.status_code >= 400:
            raise OpenRouterError(
                f"API {path} failed ({response.status_code}): {response.text[:500]}",
                status=response.status_code,
            )
        return response.json()


class OpenAIStream:
    """Incremental SSE parser for OpenAI-compatible streaming completions.

    Call :meth:`open` to send the request (raising OpenRouterError on non-2xx),
    then iterate over the object to receive content tokens as strings.
    """

    def __init__(
        self,
        client: httpx.Client,
        model: str,
        system: str,
        user: str,
        *,
        max_tokens: int,
    ) -> None:
        self._client = client
        self._cm: httpx._types.ContextManager | None = None
        self._response: httpx.Response | None = None
        self._lines: "Iterator[str]" | None = None
        self._model = model
        self._body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": True,
        }

    def open(self) -> None:
        cm = self._client.stream(
            "POST",
            "/chat/completions",
            json=self._body,
            timeout=httpx.Timeout(30, read=180),
        )
        try:
            response = cm.__enter__()
        except httpx.HTTPError as exc:
            raise OpenRouterError(
                f"API /chat/completions failed (network error): {exc}", status=None
            ) from exc
        self._cm = cm
        self._response = response
        if response.status_code >= 400:
            detail = response.read().decode(errors="replace")[:500]
            self.close()
            raise OpenRouterError(
                f"API /chat/completions failed ({response.status_code}): {detail}",
                status=response.status_code,
            )
        self._lines = response.iter_lines()

    def __iter__(self) -> "OpenAIStream":
        return self

    def __next__(self) -> str:
        """Yield the next content token; raise StopIteration when done."""
        if self._lines is None:
            raise StopIteration
        for line in self._lines:
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                self.close()
                raise StopIteration
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = (choices[0].get("delta") or {}).get("content")
            if delta:
                return delta
        # stream ended without [DONE]
        self.close()
        raise StopIteration

    def close(self) -> None:
        cm, self._cm = self._cm, None
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            finally:
                self._response = None


def build_embedder() -> ApiClient:
    """Client for the configured embedding provider."""
    return ApiClient(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        key_env_var="EMBEDDING_API_KEY",
        model=settings.embedding_model,
    )


def build_llm() -> ApiClient:
    """Client for LLM chat completions (NVIDIA free chat by default)."""
    return ApiClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        key_env_var="LLM_API_KEY",
    )


def _fallback_api_key() -> str:
    return settings.llm_fallback_api_key or settings.embedding_api_key


def build_llm_fallback() -> ApiClient:
    """Client for the cross-provider chat fallback (e.g. NVIDIA free chat).

    Uses the embedding API key by default so no extra key is required; the
    endpoint is OpenAI-compatible so the same client logic applies.
    """
    return ApiClient(
        api_key=_fallback_api_key(),
        base_url=settings.llm_fallback_base_url,
        key_env_var="LLM_FALLBACK_API_KEY",
        model=settings.llm_fallback_model,
    )


def _retryable(status: int | None) -> bool:
    return status is None or status in {429, 500, 502, 503}


def _chat_with_nvidia_fallback(
    system: str, user: str, *, max_tokens: int, last_error: OpenRouterError | None
) -> str:
    """Fallback chat completion against the NVIDIA-free endpoint with backoff."""
    if not _fallback_api_key():
        raise OpenRouterError(f"All configured models failed: {last_error}")
    client = build_llm_fallback()
    model = settings.llm_fallback_model
    for attempt in range(4):
        try:
            data = client._post(
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
            if _retryable(exc.status) and attempt < 3:
                print(f"[llm] fallback model {model!r} retry ({exc.status}, attempt {attempt + 1})")
                time.sleep(2**attempt * 1.5)
                continue
            break
    raise OpenRouterError(f"All configured models failed: {last_error}")


def _stream_with_nvidia_fallback(
    system: str, user: str, *, max_tokens: int, last_error: OpenRouterError | None
) -> OpenAIStream:
    """Fallback streaming completion against the NVIDIA-free endpoint."""
    if not _fallback_api_key():
        raise OpenRouterError(f"All configured models failed: {last_error}")
    client = build_llm_fallback()
    model = settings.llm_fallback_model
    for attempt in range(4):
        stream = OpenAIStream(client._client, model, system, user, max_tokens=max_tokens)
        try:
            stream.open()
        except OpenRouterError as exc:
            last_error = exc
            if _retryable(exc.status) and attempt < 3:
                print(f"[llm] fallback model {model!r} retry ({exc.status}, attempt {attempt + 1})")
                time.sleep(2**attempt * 1.5)
                continue
            break
        return stream
    raise OpenRouterError(f"All configured models failed: {last_error}")

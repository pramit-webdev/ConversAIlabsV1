"""Application configuration loaded from environment variables (.env supported)."""
import os

from dotenv import load_dotenv

load_dotenv()

# Embedding provider presets: (base_url, default model, default dimensions)
EMBEDDING_PROVIDERS = {
    "nvidia": ("https://integrate.api.nvidia.com/v1", "nvidia/nemotron-3-embed-1b", 2048),
    "openrouter": ("https://openrouter.ai/api/v1", "nvidia/nemotron-3-embed-1b:free", 2048),
    "groq": ("https://api.groq.com/openai/v1", "nomic-embed-text-v1_5", 768),
}


def _csv(value: str | None) -> list[str]:
    return [m.strip() for m in (value or "").split(",") if m.strip()]


class Settings:
    def __init__(self) -> None:
        # LLM generation (NVIDIA free chat by default; OPENROUTER_* vars switch to OpenRouter)
        self.llm_base_url: str = os.getenv("LLM_BASE_URL", "").strip() or "https://integrate.api.nvidia.com/v1"
        llm_api_key = os.getenv("LLM_API_KEY", "").strip()
        if not llm_api_key:
            # NVIDIA endpoints reuse the embedding key; otherwise use the OpenRouter key
            if "nvidia.com" in self.llm_base_url:
                llm_api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
            llm_api_key = llm_api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.llm_api_key: str = llm_api_key
        self.llm_model: str = os.getenv("LLM_MODEL", "").strip() or "minimaxai/minimax-m3"
        self.llm_fallback_models: list[str] = _csv(os.getenv("LLM_FALLBACK_MODELS", ""))
        # Cross-provider fallback (e.g. NVIDIA free chat) used when every
        # configured model is unavailable; reuses the embedding API key unless
        # a dedicated LLM_FALLBACK_API_KEY is provided.
        self.llm_fallback_base_url: str = os.getenv(
            "LLM_FALLBACK_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self.llm_fallback_api_key: str = os.getenv("LLM_FALLBACK_API_KEY", "")
        self.llm_fallback_model: str = os.getenv("LLM_FALLBACK_MODEL", "").strip() or "meta/llama-3.1-8b-instruct"

        # Embeddings (provider-agnostic: nvidia | openrouter | groq)
        provider = os.getenv("EMBEDDING_PROVIDER", "nvidia").strip().lower()
        default_url, default_model, default_dim = EMBEDDING_PROVIDERS.get(
            provider, EMBEDDING_PROVIDERS["nvidia"]
        )
        self.embedding_provider: str = provider
        self.embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", default_url)
        self.embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", default_model)
        self.embedding_dim: int = int(os.getenv("EMBEDDING_DIM", str(default_dim)))

        # Qdrant
        self.qdrant_url: str = os.getenv("QDRANT_URL", "")
        self.qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
        self.qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "pdf_rag")

        # Retrieval
        self.retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))
        self.retrieval_score_threshold: float = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.30"))

        # Chunking (word counts)
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "400"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "60"))

        # Batch size for embedding requests
        self.max_embed_batch: int = int(os.getenv("MAX_EMBED_BATCH", "32"))


settings = Settings()

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
        # OpenRouter (LLM generation, required by the assignment)
        self.openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        self.llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free")
        self.llm_fallback_models: list[str] = _csv(os.getenv("LLM_FALLBACK_MODELS", ""))

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
        self.retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
        self.retrieval_score_threshold: float = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.30"))

        # Chunking (word counts)
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "400"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "60"))

        # Batch size for embedding requests
        self.max_embed_batch: int = int(os.getenv("MAX_EMBED_BATCH", "32"))


settings = Settings()

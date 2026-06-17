"""
Central LLM / embedding provider config.

Switch providers entirely through environment variables — no code changes.
Ollama, Groq, and OpenAI all speak the OpenAI-compatible API, so the only
thing that changes between local dev and cloud hosting is a few env vars.

  Local (free, default):   LLM_PROVIDER=ollama   (Ollama on your machine)
  Cloud (free tier):       LLM_PROVIDER=groq     + GROQ_API_KEY
  Cloud (paid):            LLM_PROVIDER=openai   + OPENAI_API_KEY
"""

import os

# ---------------------------------------------------------------------------
# Chat / report LLM
# ---------------------------------------------------------------------------

def llm_config() -> dict:
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()

    if provider == "groq":
        return {
            "provider": "groq",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key":  os.environ.get("GROQ_API_KEY", ""),
            "model":    os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        }
    if provider == "hermes":
        # Nous Research Hermes — OpenAI-compatible. Set HERMES_BASE_URL to the
        # endpoint they give you (hosted Nous API, OpenRouter, or self-hosted vLLM).
        return {
            "provider": "hermes",
            "base_url": os.environ.get("HERMES_BASE_URL", ""),     # e.g. https://inference.nousresearch.com/v1
            "api_key":  os.environ.get("HERMES_API_KEY", ""),      # fill when they hand you the key
            "model":    os.environ.get("HERMES_MODEL", "Hermes-3-Llama-3.1-70B"),
        }
    if provider == "openai":
        return {
            "provider": "openai",
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "api_key":  os.environ.get("OPENAI_API_KEY", ""),
            "model":    os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        }
    # default: ollama (local, free)
    return {
        "provider": "ollama",
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "api_key":  "ollama",  # Ollama ignores the key; SDK requires a non-empty string
        "model":    os.environ.get("OLLAMA_MODEL", "llama3.2"),
    }


# ---------------------------------------------------------------------------
# Embeddings (for the RAG notes store)
# ---------------------------------------------------------------------------

def embed_config() -> dict:
    """Embeddings are always computed via an OpenAI-compatible /embeddings call.
    Groq has no embeddings API, so when chatting via Groq you embed via Ollama
    (local) or OpenAI (cloud)."""
    provider = os.environ.get("EMBED_PROVIDER", "ollama").lower()

    # No embedding backend (e.g. free cloud tier with no Ollama/OpenAI). Notes
    # still save via a deterministic fallback vector; semantic search is skipped.
    if provider in ("none", "skip", "disabled", "off"):
        return {"provider": "none", "style": "none"}

    if provider == "openai":
        return {
            "provider": "openai",
            "url":      os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/embeddings",
            "api_key":  os.environ.get("OPENAI_API_KEY", ""),
            "model":    os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
            "style":    "openai",
        }
    # default: ollama (local, free)
    return {
        "provider": "ollama",
        "url":      os.environ.get("OLLAMA_BASE", "http://localhost:11434") + "/api/embeddings",
        "api_key":  "",
        "model":    os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        "style":    "ollama",
    }

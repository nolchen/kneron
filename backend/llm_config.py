"""
Central LLM / embedding provider config.

Switch providers entirely through environment variables — no code changes.
Ollama, Groq, and OpenAI all speak the OpenAI-compatible API, so the only
thing that changes between local dev and cloud hosting is a few env vars.

  Local (free, default):   LLM_PROVIDER=ollama   (Ollama on your machine)
  Cloud (free tier):       LLM_PROVIDER=groq     + GROQ_API_KEY
  Cloud (paid):            LLM_PROVIDER=openai   + OPENAI_API_KEY
  Private / on-prem:       LLM_PROVIDER=kneo     + KNEO_BASE_URL/KNEO_MODEL  (Kneron KNEO 350)
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
    if provider == "kneo":
        # Kneron KNEO 350 — private, on-prem edge AI (OpenClaw / KneoChat). Keeps
        # all PM data inside the company; nothing goes to a cloud LLM.
        #
        # ASSUMES an OpenAI-compatible endpoint, i.e. POST {base_url}/chat/completions.
        # Confirm with the internal KNEO team before relying on this:
        #   1. base URL of the API            -> KNEO_BASE_URL (e.g. http://kneo-350.internal:8000/v1)
        #   2. whether it needs a key/token   -> KNEO_API_KEY  (left as a non-empty
        #                                        placeholder below; KNEO may ignore it)
        #   3. the served model name          -> KNEO_MODEL
        # If KNEO turns out NOT to be OpenAI-compatible (proprietary request/response
        # shape), this branch stays but pm_agent needs a small adapter for it instead
        # of the plain `openai` SDK call.
        return {
            "provider": "kneo",
            "base_url": os.environ.get("KNEO_BASE_URL", ""),
            "api_key":  os.environ.get("KNEO_API_KEY", "kneo"),  # non-empty: the openai SDK requires it
            "model":    os.environ.get("KNEO_MODEL", ""),
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
    if provider == "kneo":
        # KNEO embeddings, assuming an OpenAI-compatible /embeddings endpoint.
        # If KNEO has no embeddings API, set EMBED_PROVIDER=none (notes still save
        # via the fallback vector, semantic search disabled) or point EMBED_PROVIDER
        # at ollama/openai while only chat runs on KNEO.
        return {
            "provider": "kneo",
            "url":      os.environ.get("KNEO_BASE_URL", "") + "/embeddings",
            "api_key":  os.environ.get("KNEO_API_KEY", "kneo"),
            "model":    os.environ.get("KNEO_EMBED_MODEL", ""),
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

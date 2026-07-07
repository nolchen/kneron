"""
RAG-powered notes store.
Saves reports/summaries as searchable vector embeddings using ChromaDB + nomic-embed-text.
Thread-safe: uses a lock so concurrent FastAPI requests don't conflict on the SQLite file.
"""

import os
import hashlib
import threading
import uuid
import httpx
import chromadb
from datetime import datetime, timezone
from pathlib import Path

from llm_config import embed_config

# Dimension of the deterministic fallback vector used when no embedding backend
# is reachable. Lets reports save (and list/display) even with no Ollama/OpenAI.
_FALLBACK_DIM = 256


def _fallback_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding so notes can still be stored when no real
    embedding provider is available (free cloud tier). Semantic search is
    effectively disabled, but reports save, list, and display normally."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    return [(h[i % len(h)] / 127.5) - 1.0 for i in range(_FALLBACK_DIM)]

# Honor DATA_DIR so the vector store can live on a persistent volume in production.
_DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
DB_PATH   = str(_DATA_DIR / "notes_db")

_lock = threading.Lock()


def _embed(text: str) -> list[float]:
    cfg = embed_config()
    if cfg["style"] == "none":
        raise RuntimeError("embeddings disabled (EMBED_PROVIDER=none)")
    if cfg["style"] == "openai":
        headers = {"Authorization": f"Bearer {cfg['api_key']}"}
        r = httpx.post(cfg["url"], headers=headers,
                       json={"model": cfg["model"], "input": text}, timeout=30)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    # ollama style
    r = httpx.post(cfg["url"], json={"model": cfg["model"], "prompt": text}, timeout=30)
    r.raise_for_status()
    return r.json()["embedding"]


class NotesStore:
    def __init__(self):
        self._client     = chromadb.PersistentClient(path=DB_PATH)
        self._collection = self._client.get_or_create_collection("pm_notes")

    def save(self, title: str, content: str, note_type: str = "report",
             owner: str = "", note_id: str | None = None) -> dict:
        """Persist a note. `owner` tags who it belongs to (e.g. the inbox an
        email came from) so callers can scope visibility. Pass a stable
        `note_id` to make re-saving the same item idempotent (upsert) — used for
        emails so re-scanning an inbox doesn't create duplicate notes/graph nodes."""
        note_id   = note_id or str(uuid.uuid4())
        try:
            embedding = _embed(content)
        except Exception as e:
            print(f"[notes] Embedding unavailable, saving without semantic search: {e}")
            embedding = _fallback_embedding(content)
        created   = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with _lock:
            self._collection.upsert(
                ids=[note_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"title": title, "type": note_type,
                            "owner": owner, "created_at": created}],
            )
        return {"id": note_id, "title": title, "type": note_type,
                "owner": owner, "content": content, "created_at": created}

    def search(self, query: str, n: int = 3) -> list[dict]:
        with _lock:
            total = self._collection.count()
            if total == 0:
                return []
            try:
                embedding = _embed(query)
            except Exception as e:
                print(f"[notes] Embedding unavailable, semantic search disabled: {e}")
                return []
            results   = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(n, total),
            )
        return [
            {
                "content":    results["documents"][0][i],
                "title":      results["metadatas"][0][i]["title"],
                "type":       results["metadatas"][0][i]["type"],
                "owner":      results["metadatas"][0][i].get("owner", ""),
                "created_at": results["metadatas"][0][i]["created_at"],
            }
            for i in range(len(results["documents"][0]))
        ]

    def list_all(self) -> list[dict]:
        with _lock:
            if self._collection.count() == 0:
                return []
            res = self._collection.get()
        notes = [
            {"id": res["ids"][i], "content": res["documents"][i], **res["metadatas"][i]}
            for i in range(len(res["ids"]))
        ]
        return sorted(notes, key=lambda n: n["created_at"], reverse=True)

    def delete(self, note_id: str):
        with _lock:
            self._collection.delete(ids=[note_id])

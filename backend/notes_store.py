"""
RAG-powered notes store.
Saves reports/summaries as searchable vector embeddings using ChromaDB + nomic-embed-text.
Thread-safe: uses a lock so concurrent FastAPI requests don't conflict on the SQLite file.
"""

import threading
import uuid
import httpx
import chromadb
from datetime import datetime
from pathlib import Path

OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
DB_PATH     = str(Path(__file__).parent / "notes_db")

_lock = threading.Lock()


def _embed(text: str) -> list[float]:
    r = httpx.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["embedding"]


class NotesStore:
    def __init__(self):
        self._client     = chromadb.PersistentClient(path=DB_PATH)
        self._collection = self._client.get_or_create_collection("pm_notes")

    def save(self, title: str, content: str, note_type: str = "report") -> dict:
        note_id   = str(uuid.uuid4())
        embedding = _embed(content)
        created   = datetime.utcnow().isoformat()
        with _lock:
            self._collection.add(
                ids=[note_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"title": title, "type": note_type, "created_at": created}],
            )
        return {"id": note_id, "title": title, "type": note_type,
                "content": content, "created_at": created}

    def search(self, query: str, n: int = 3) -> list[dict]:
        with _lock:
            total = self._collection.count()
            if total == 0:
                return []
            embedding = _embed(query)
            results   = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(n, total),
            )
        return [
            {
                "content":    results["documents"][0][i],
                "title":      results["metadatas"][0][i]["title"],
                "type":       results["metadatas"][0][i]["type"],
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

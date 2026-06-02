"""
Obsidian vault bridge.
Reads .md files from the vault into ChromaDB, and writes reports back as .md files.
Obsidian picks up new files automatically — no plugin or API needed.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional

VAULT_PATH = Path(__file__).parent.parent / "PM-Vault"
PM_FOLDER  = VAULT_PATH / "PM-Agent"   # sub-folder for app-generated notes


def _ensure_folder():
    PM_FOLDER.mkdir(parents=True, exist_ok=True)


def _safe_filename(title: str) -> str:
    """Turn a title into a unique safe .md filename."""
    import uuid as _uuid
    name = re.sub(r'[\\/:*?"<>|]', "", title)
    name = re.sub(r"\s+", " ", name).strip()
    suffix = _uuid.uuid4().hex[:6]  # short unique suffix — prevents filename conflicts
    return f"{name[:70]} {suffix}.md"


def _frontmatter(title: str, note_type: str, created: str) -> str:
    return (
        f"---\n"
        f"title: \"{title}\"\n"
        f"type: {note_type}\n"
        f"created: {created}\n"
        f"tags: [pm-agent, {note_type}]\n"
        f"---\n\n"
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_note(title: str, content: str, note_type: str = "report") -> Path:
    """Save a note/report as a .md file in the vault's PM-Agent subfolder."""
    _ensure_folder()
    created  = datetime.utcnow().isoformat()
    filename = _safe_filename(title)
    path     = PM_FOLDER / filename
    body     = _frontmatter(title, note_type, created) + f"# {title}\n\n{content}"
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Read & index
# ---------------------------------------------------------------------------

def _parse_md(path: Path) -> Optional[dict]:
    """Parse a .md file, strip frontmatter, return metadata + body."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Strip YAML frontmatter if present
    meta = {"title": path.stem, "type": "note", "created_at": ""}
    body = text

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm   = text[3:end]
            body = text[end + 3:].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"')

    if not meta.get("created_at"):
        stat = path.stat()
        meta["created_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

    if not body.strip():
        return None

    return {
        "title":      meta.get("title", path.stem),
        "type":       meta.get("type", "note"),
        "created_at": meta["created_at"],
        "content":    body,
        "source":     str(path),
    }


def scan_vault() -> list[dict]:
    """Return all readable .md files in the vault as parsed dicts."""
    if not VAULT_PATH.exists():
        return []
    notes = []
    for md_file in VAULT_PATH.rglob("*.md"):
        parsed = _parse_md(md_file)
        if parsed:
            notes.append(parsed)
    return notes

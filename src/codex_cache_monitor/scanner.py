from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def default_codex_home() -> Path:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / ".codex"


def resolve_codex_home(codex_home: Path | None = None) -> Path:
    if codex_home is not None:
        return codex_home.expanduser().resolve()
    return default_codex_home().expanduser().resolve()


def sessions_path(codex_home: Path | None = None) -> Path:
    return resolve_codex_home(codex_home) / "sessions"


def scan_session_files(codex_home: Path | None = None) -> list[Path]:
    root = sessions_path(codex_home)
    if not root.exists() or not root.is_dir():
        return []

    files = [path for path in root.rglob("*.jsonl") if path.is_file()]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def file_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)

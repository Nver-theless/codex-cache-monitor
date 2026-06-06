from __future__ import annotations

from pathlib import Path

from .models import DoctorReport
from .parser import parse_session_file
from .scanner import resolve_codex_home, scan_session_files, sessions_path


def inspect_environment(codex_home: Path | None = None) -> DoctorReport:
    resolved_home = resolve_codex_home(codex_home)
    session_root = sessions_path(resolved_home)
    files = scan_session_files(resolved_home)

    usage_files = 0
    skipped_files = 0
    recent_time = None

    for index, file_path in enumerate(files):
        if index == 0:
            recent_time = parse_session_file(file_path).last_modified
        metrics = parse_session_file(file_path)
        if metrics.usage is None:
            skipped_files += 1
        else:
            usage_files += 1

    hints: list[str] = []
    if not session_root.exists():
        hints.append("sessions path was not found; run Codex first or pass --codex-home")
    elif not files:
        hints.append("no JSONL session files were found")
    elif usage_files == 0:
        hints.append("no token usage found; Codex CLI may be old or the log format may be unsupported")
    elif skipped_files:
        hints.append("some files were skipped because usage data was missing or incomplete")

    return DoctorReport(
        codex_home=resolved_home,
        sessions_path=session_root,
        sessions_path_exists=session_root.exists(),
        jsonl_files=len(files),
        usage_files=usage_files,
        skipped_files=skipped_files,
        recent_session_time=recent_time,
        hints=hints,
    )

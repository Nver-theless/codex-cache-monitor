from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    @property
    def non_cached_input_tokens(self) -> int:
        return max(self.input_tokens - self.cached_input_tokens, 0)


@dataclass
class SessionMetrics:
    file_path: Path
    last_modified: datetime
    usage: TokenUsage | None
    skipped_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_skipped(self) -> bool:
        return self.usage is None or self.skipped_reason is not None


@dataclass
class AggregateMetrics:
    usage: TokenUsage
    parsed_sessions: int
    skipped_sessions: int
    sessions: list[SessionMetrics]
    warnings: list[str] = field(default_factory=list)


@dataclass
class DoctorReport:
    codex_home: Path
    sessions_path: Path
    sessions_path_exists: bool
    jsonl_files: int
    usage_files: int
    skipped_files: int
    recent_session_time: datetime | None
    hints: list[str] = field(default_factory=list)

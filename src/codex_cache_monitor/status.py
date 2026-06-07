from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .metrics import cache_hit_rate, cache_status
from .models import AggregateMetrics
from .render import format_compact_number


DEFAULT_STATE_FILE = Path.home() / ".codex-cache-monitor" / "status.json"


def build_status_payload(
    aggregate: AggregateMetrics,
    updated_at: datetime | None = None,
) -> dict[str, Any]:
    usage = aggregate.usage
    rate = cache_hit_rate(usage)
    return {
        "cache_hit_rate": round(rate, 6),
        "cache_hit_rate_percent": round(rate * 100, 1),
        "status": cache_status(rate),
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "non_cached_input_tokens": usage.non_cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_output_tokens": usage.reasoning_output_tokens,
        "total_tokens": usage.total_tokens,
        "parsed_sessions": aggregate.parsed_sessions,
        "skipped_sessions": aggregate.skipped_sessions,
        "updated_at": (updated_at or datetime.now()).replace(microsecond=0).isoformat(),
    }


def format_status_line(payload: dict[str, Any]) -> str:
    return (
        f"Codex Cache: {payload['cache_hit_rate_percent']:.1f}% {payload['status']} · "
        f"Input {format_compact_number(int(payload['input_tokens']))} · "
        f"Cached {format_compact_number(int(payload['cached_input_tokens']))} · "
        f"Skipped {payload['skipped_sessions']}"
    )


def format_plain_status(payload: dict[str, Any]) -> str:
    return f"{payload['cache_hit_rate_percent']:.1f}% {payload['status']}"


def status_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def write_status_file(payload: dict[str, Any], state_file: Path | None = None) -> Path:
    path = (state_file or DEFAULT_STATE_FILE).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status_json(payload) + "\n", encoding="utf-8")
    return path


def display_state_path(path: Path) -> str:
    expanded_default = DEFAULT_STATE_FILE.expanduser()
    try:
        if path.expanduser().resolve() == expanded_default.resolve():
            return "~/.codex-cache-monitor/status.json"
    except OSError:
        pass
    return str(path)

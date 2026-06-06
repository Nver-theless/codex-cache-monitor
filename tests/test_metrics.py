from __future__ import annotations

from datetime import datetime
from pathlib import Path

from codex_cache_monitor.metrics import aggregate_sessions, cache_hit_rate, cache_status
from codex_cache_monitor.models import SessionMetrics, TokenUsage


def session(name: str, usage: TokenUsage | None, skipped_reason: str | None = None) -> SessionMetrics:
    return SessionMetrics(
        file_path=Path(name),
        last_modified=datetime(2026, 6, 6, 20, 0, 0),
        usage=usage,
        skipped_reason=skipped_reason,
    )


def test_cache_hit_rate_handles_zero_input() -> None:
    assert cache_hit_rate(TokenUsage(input_tokens=0, cached_input_tokens=10)) == 0.0


def test_cache_status_thresholds() -> None:
    assert cache_status(0.7) == "GOOD"
    assert cache_status(0.3) == "NORMAL"
    assert cache_status(0.29) == "LOW"


def test_aggregate_sessions_counts_and_sums() -> None:
    aggregate = aggregate_sessions(
        [
            session("one.jsonl", TokenUsage(100, 70, 10, 5, 115)),
            session("two.jsonl", TokenUsage(50, 20, 8, 2, 60)),
            session("bad.jsonl", None, "no token usage found"),
        ]
    )

    assert aggregate.parsed_sessions == 2
    assert aggregate.skipped_sessions == 1
    assert aggregate.usage.input_tokens == 150
    assert aggregate.usage.cached_input_tokens == 90
    assert aggregate.usage.non_cached_input_tokens == 60
    assert aggregate.usage.output_tokens == 18
    assert aggregate.usage.reasoning_output_tokens == 7
    assert aggregate.usage.total_tokens == 175

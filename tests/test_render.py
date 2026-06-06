from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console

from codex_cache_monitor.metrics import aggregate_sessions
from codex_cache_monitor.models import SessionMetrics, TokenUsage
from codex_cache_monitor.render import render_sessions, render_summary


LONG_FILE = "rollout-2026-06-06T21-11-58-019e9d0f-cc40-7fa1-bba4-263249ba3997.jsonl"


def make_sessions() -> list[SessionMetrics]:
    return [
        SessionMetrics(
            file_path=Path(LONG_FILE),
            last_modified=datetime(2026, 6, 6, 21, 48),
            usage=TokenUsage(
                input_tokens=4_415_135,
                cached_input_tokens=4_085_120,
                output_tokens=22_100,
                reasoning_output_tokens=1_400,
                total_tokens=4_437_235,
            ),
        ),
        SessionMetrics(
            file_path=Path("skipped-session.jsonl"),
            last_modified=datetime(2026, 6, 6, 21, 11),
            usage=None,
            skipped_reason="usage missing because this fixture has no token usage payload",
        ),
    ]


def render_to_text(renderable: object, width: int) -> str:
    console = Console(width=width, record=True, force_terminal=False)
    console.print(renderable)
    return console.export_text()


def test_summary_render_is_stable_at_common_widths() -> None:
    aggregate = aggregate_sessions(make_sessions())

    for width in (60, 80, 120):
        output = render_to_text(render_summary(aggregate, width=width), width)
        assert "Codex Cache Monitor" in output
        assert "Cache Hit Rate" in output
        assert "Recent" in output
        assert "Skipp\ned" not in output
        assert "Reaso\nn" not in output
        assert LONG_FILE not in output


def test_summary_compact_mode_uses_list_not_wide_table() -> None:
    aggregate = aggregate_sessions(make_sessions())

    output = render_to_text(render_summary(aggregate, width=60), 60)

    assert "Codex Cache Monitor" in output
    assert "Recent" in output
    assert "Session File" not in output
    assert "Skipped Reason" not in output
    assert "Reasoning Tokens" not in output
    assert "│ Metric │ Value │" not in output
    assert "Input" in output
    assert "4.4M" in output


def test_sessions_render_truncates_long_file_names() -> None:
    output = render_to_text(render_sessions(make_sessions(), width=160), 160)

    assert "Sessions" in output
    assert LONG_FILE not in output
    assert "rollout-2026-06-06" in output
    assert "..." in output
    assert "Skipp\ned" not in output
    assert "Reaso\nn" not in output


def test_sessions_render_hides_detail_columns_at_medium_width() -> None:
    output = render_to_text(render_sessions(make_sessions(), width=100), 100)

    assert "File" not in output
    assert "Reasoning" not in output
    assert "Skipped Reason" not in output
    assert "Hit Rate" in output
    assert "4.4M" in output


def test_sessions_render_compact_mode_is_minimal() -> None:
    output = render_to_text(render_sessions(make_sessions(), width=60), 60)

    assert "Last Activity" in output
    assert "Input" in output
    assert "Hit Rate" in output
    assert "Status" in output
    assert "File" not in output
    assert "Cached" not in output
    assert "Skipped Reason" not in output

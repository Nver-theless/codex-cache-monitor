from __future__ import annotations

import json
from pathlib import Path

from codex_cache_monitor.parser import parse_session_file


def write_jsonl(path: Path, rows: list[object]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_prefers_last_total_token_usage_fixture() -> None:
    path = Path(__file__).parent / "fixtures" / "sample-session.jsonl"

    metrics = parse_session_file(path)

    assert metrics.usage is not None
    assert metrics.usage.input_tokens == 300
    assert metrics.usage.cached_input_tokens == 240
    assert metrics.usage.output_tokens == 30
    assert metrics.usage.reasoning_output_tokens == 10
    assert metrics.usage.total_tokens == 340
    assert metrics.skipped_reason is None
    assert metrics.warnings


def test_extracts_top_level_token_count(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    write_jsonl(
        path,
        [
            {
                "token_count": {
                    "input_tokens": 50,
                    "cached_input_tokens": 25,
                    "output_tokens": 7,
                    "reasoning_output_tokens": 3,
                    "total_tokens": 60,
                }
            }
        ],
    )

    metrics = parse_session_file(path)

    assert metrics.usage is not None
    assert metrics.usage.input_tokens == 50
    assert metrics.usage.cached_input_tokens == 25


def test_extracts_event_msg_json_usage(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    write_jsonl(
        path,
        [
            {
                "event_msg": json.dumps(
                    {
                        "payload": {
                            "info": {
                                "last_token_usage": {
                                    "input_tokens": 40,
                                    "cached_input_tokens": 12,
                                    "output_tokens": 5,
                                    "reasoning_output_tokens": 2,
                                    "total_tokens": 47,
                                }
                            }
                        }
                    }
                )
            }
        ],
    )

    metrics = parse_session_file(path)

    assert metrics.usage is not None
    assert metrics.usage.input_tokens == 40
    assert metrics.usage.cached_input_tokens == 12


def test_skips_file_with_no_usage(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    write_jsonl(path, [{"type": "message", "payload": {"text": "not inspected"}}])

    metrics = parse_session_file(path)

    assert metrics.usage is None
    assert metrics.skipped_reason == "no token usage found"


def test_skips_zero_input_tokens(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    write_jsonl(path, [{"token_count": {"input_tokens": 0, "cached_input_tokens": 0}}])

    metrics = parse_session_file(path)

    assert metrics.usage is None
    assert metrics.skipped_reason == "missing or zero input tokens"

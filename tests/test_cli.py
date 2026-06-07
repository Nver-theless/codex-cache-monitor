from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from codex_cache_monitor.cli import app

runner = CliRunner()


def make_codex_home(tmp_path: Path) -> Path:
    codex_home = tmp_path / ".codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    sample = Path(__file__).parent / "fixtures" / "sample-session.jsonl"
    (sessions / "sample-session.jsonl").write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
    return codex_home


def write_session(sessions: Path, name: str, content: str, mtime: int) -> None:
    path = sessions / name
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def make_multi_codex_home(tmp_path: Path) -> Path:
    codex_home = tmp_path / ".codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    write_session(
        sessions,
        "recent.jsonl",
        json.dumps(
            {
                "payload": {
                    "info": {
                        "total_token_usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 80,
                            "output_tokens": 10,
                            "reasoning_output_tokens": 5,
                            "total_tokens": 115,
                        }
                    }
                }
            }
        ),
        300,
    )
    write_session(
        sessions,
        "older.jsonl",
        json.dumps(
            {
                "token_count": {
                    "input_tokens": 50,
                    "cached_input_tokens": 20,
                    "output_tokens": 5,
                    "reasoning_output_tokens": 2,
                    "total_tokens": 57,
                }
            }
        ),
        200,
    )
    write_session(
        sessions,
        "private-skipped.jsonl",
        json.dumps(
            {
                "prompt": "secret prompt",
                "response": "secret response",
                "tool_output": "secret tool output",
            }
        ),
        100,
    )
    return codex_home


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "codex-cache" in result.output or "prompt cache" in result.output


def test_bare_command_shows_summary(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)

    result = runner.invoke(app, ["--codex-home", str(codex_home)])

    assert result.exit_code == 0
    assert "Codex Cache Monitor" in result.output


def test_doctor_summary_sessions_and_export(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)

    doctor = runner.invoke(app, ["doctor", "--codex-home", str(codex_home)])
    assert doctor.exit_code == 0
    assert "Codex Cache Doctor" in doctor.output

    summary = runner.invoke(app, ["summary", "--codex-home", str(codex_home)])
    assert summary.exit_code == 0
    assert "Codex Cache Monitor" in summary.output

    sessions = runner.invoke(app, ["sessions", "--codex-home", str(codex_home)])
    assert sessions.exit_code == 0
    assert "Recent Sessions" in sessions.output or "Sessions" in sessions.output

    exported = runner.invoke(app, ["export", "--json", "--codex-home", str(codex_home)])
    assert exported.exit_code == 0
    payload = json.loads(exported.output)
    assert payload["summary"]["input_tokens"] == 300
    assert payload["summary"]["cached_input_tokens"] == 240
    assert "summary" in payload
    assert "sessions" in payload
    assert "warnings" in payload
    assert isinstance(payload["sessions"], list)
    assert isinstance(payload["warnings"], list)
    assert payload["sessions"][0]["file"] == "sample-session.jsonl"
    assert "file_path" not in payload["sessions"][0]
    assert "usage" not in payload["sessions"][0]


def test_export_summary_is_full_and_sessions_are_limited(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    exported = runner.invoke(app, ["export", "--json", "--limit", "1", "--codex-home", str(codex_home)])

    assert exported.exit_code == 0
    payload = json.loads(exported.output)
    assert payload["summary"]["input_tokens"] == 150
    assert payload["summary"]["cached_input_tokens"] == 100
    assert payload["summary"]["parsed_sessions"] == 2
    assert payload["summary"]["skipped_sessions"] == 1
    assert len(payload["sessions"]) == 1
    assert payload["sessions"][0]["file"] == "recent.jsonl"
    assert payload["warnings"] == ["1 session skipped because usage data was missing or incomplete"]


def test_summary_is_full_and_sessions_command_is_limited(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    summary = runner.invoke(app, ["summary", "--limit", "1", "--codex-home", str(codex_home)])
    sessions = runner.invoke(app, ["sessions", "--limit", "1", "--codex-home", str(codex_home)])

    assert summary.exit_code == 0
    assert "150" in summary.output
    assert "Recent Sessions" in summary.output
    assert "older.jsonl" not in summary.output
    assert sessions.exit_code == 0
    assert "Recent Sessions" in sessions.output or "Sessions" in sessions.output
    assert "older.jsonl" not in sessions.output


def test_export_json_does_not_leak_private_fields(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    exported = runner.invoke(app, ["export", "--json", "--limit", "10", "--codex-home", str(codex_home)])

    assert exported.exit_code == 0
    output = exported.output
    assert "secret prompt" not in output
    assert "secret response" not in output
    assert "secret tool output" not in output
    assert '"prompt"' not in output
    assert '"response"' not in output
    assert '"tool_output"' not in output


def test_cli_summary_smoke_avoids_wrapped_headers(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)

    result = runner.invoke(app, ["summary", "--codex-home", str(codex_home)])

    assert result.exit_code == 0
    assert "Codex Cache Monitor" in result.output
    assert "Recent Sessions" in result.output
    assert "Skipp\ned" not in result.output
    assert "Reaso\nn" not in result.output


def test_sessions_limit_20_smoke(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    result = runner.invoke(app, ["sessions", "--limit", "20", "--codex-home", str(codex_home)])

    assert result.exit_code == 0
    assert "Sessions" in result.output


def test_status_default_outputs_single_line(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    result = runner.invoke(app, ["status", "--codex-home", str(codex_home)])

    assert result.exit_code == 0
    assert result.output.count("\n") == 1
    assert "Codex Cache:" in result.output
    assert "%" in result.output
    assert any(status in result.output for status in ("GOOD", "NORMAL", "LOW"))
    assert "Codex Cache Monitor" not in result.output
    assert "Recent Sessions" not in result.output


def test_status_plain_outputs_short_result(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    result = runner.invoke(app, ["status", "--plain", "--codex-home", str(codex_home)])

    assert result.exit_code == 0
    assert result.output.strip() == "66.7% NORMAL"
    assert "Codex Cache Monitor" not in result.output
    assert "{" not in result.output


def test_status_json_outputs_metadata_only(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)

    result = runner.invoke(app, ["status", "--json", "--codex-home", str(codex_home)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload) == {
        "cache_hit_rate",
        "cache_hit_rate_percent",
        "status",
        "input_tokens",
        "cached_input_tokens",
        "non_cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
        "parsed_sessions",
        "skipped_sessions",
        "updated_at",
    }
    assert payload["cache_hit_rate"] == 0.666667
    assert payload["cache_hit_rate_percent"] == 66.7
    assert payload["status"] == "NORMAL"
    assert payload["input_tokens"] == 150
    assert payload["cached_input_tokens"] == 100
    assert payload["non_cached_input_tokens"] == 50
    assert payload["output_tokens"] == 15
    assert payload["reasoning_output_tokens"] == 7
    assert payload["total_tokens"] == 172
    assert payload["parsed_sessions"] == 2
    assert payload["skipped_sessions"] == 1
    assert isinstance(payload["updated_at"], str)


def test_status_write_state_to_custom_file(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)
    state_file = tmp_path / "nested" / "status.json"

    result = runner.invoke(
        app,
        [
            "status",
            "--write-state",
            "--state-file",
            str(state_file),
            "--codex-home",
            str(codex_home),
        ],
    )

    assert result.exit_code == 0
    assert f"State written to {state_file}" in result.output
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload["status"] == "NORMAL"


def test_status_json_and_state_file_do_not_leak_private_fields(tmp_path: Path) -> None:
    codex_home = make_multi_codex_home(tmp_path)
    state_file = tmp_path / "status.json"

    json_result = runner.invoke(app, ["status", "--json", "--codex-home", str(codex_home)])
    state_result = runner.invoke(
        app,
        [
            "status",
            "--write-state",
            "--state-file",
            str(state_file),
            "--codex-home",
            str(codex_home),
        ],
    )

    assert json_result.exit_code == 0
    assert state_result.exit_code == 0
    combined = json_result.output + state_file.read_text(encoding="utf-8")
    for sensitive in (
        '"prompt"',
        '"response"',
        '"tool_output"',
        "secret prompt",
        "secret response",
        "secret tool output",
        "raw JSONL",
    ):
        assert sensitive not in combined

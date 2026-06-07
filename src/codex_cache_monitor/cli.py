from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live

from .doctor import inspect_environment
from .metrics import aggregate_sessions, cache_hit_rate, cache_status, warning_messages
from .models import AggregateMetrics, SessionMetrics, TokenUsage
from .parser import parse_session_files
from .render import render_doctor, render_sessions, render_summary
from .scanner import scan_session_files
from .status import (
    build_status_payload,
    display_state_path,
    format_plain_status,
    format_status_line,
    status_json,
    write_status_file,
)

app = typer.Typer(
    help="A beautiful local terminal dashboard for Codex prompt cache visibility.",
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console()


CodexHomeOption = Annotated[
    Path | None,
    typer.Option("--codex-home", help="Path to the Codex home directory."),
]
LimitOption = Annotated[int, typer.Option("--limit", min=1, help="Limit recent sessions displayed or exported.")]
VerboseOption = Annotated[bool, typer.Option("--verbose", help="Show extra warnings and details.")]


@app.callback()
def main(
    ctx: typer.Context,
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
) -> None:
    if ctx.invoked_subcommand is None:
        _show_summary(codex_home, limit, verbose)


@app.command()
def summary(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
) -> None:
    """Show the cache dashboard."""
    _show_summary(codex_home, limit, verbose)


@app.command()
def sessions(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
) -> None:
    """Show recent session cache metrics."""
    parsed = _load_recent_sessions(codex_home, limit)
    if not verbose:
        for session in parsed:
            session.warnings = []
    console.print(render_sessions(parsed, width=console.size.width))


@app.command()
def status(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
    plain: Annotated[bool, typer.Option("--plain", help="Print only the cache hit rate and status.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Write machine-readable JSON.")] = False,
    write_state: Annotated[bool, typer.Option("--write-state", help="Write the local status JSON file.")] = False,
    state_file: Annotated[
        Path | None,
        typer.Option("--state-file", help="Path for --write-state output."),
    ] = None,
) -> None:
    """Show a compact cache status for scripts and integrations."""
    del limit
    aggregate = _load_full_aggregate(codex_home, verbose)
    payload = build_status_payload(aggregate)

    written_path = None
    if write_state:
        written_path = write_status_file(payload, state_file)

    if json_output:
        typer.echo(status_json(payload))
    elif write_state and written_path is not None:
        typer.echo(f"State written to {display_state_path(written_path)}")
    elif plain:
        typer.echo(format_plain_status(payload))
    else:
        typer.echo(format_status_line(payload))


@app.command()
def watch(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
    interval: Annotated[float, typer.Option("--interval", min=0.5, help="Refresh interval in seconds.")] = 3.0,
) -> None:
    """Refresh the dashboard continuously."""
    with Live(console=console, screen=True, refresh_per_second=4) as live:
        while True:
            aggregate = _load_full_aggregate(codex_home, verbose)
            live.update(render_summary(aggregate, limit=limit, width=console.size.width))
            time.sleep(interval)


@app.command()
def doctor(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
) -> None:
    """Check Codex session log availability and support."""
    del limit, verbose
    console.print(render_doctor(inspect_environment(codex_home)))


@app.command("export")
def export_command(
    codex_home: CodexHomeOption = None,
    limit: LimitOption = 10,
    verbose: VerboseOption = False,
    json_output: Annotated[bool, typer.Option("--json", help="Write machine-readable JSON.")] = False,
) -> None:
    """Export cache metrics."""
    if not json_output:
        raise typer.BadParameter("export currently requires --json")
    aggregate = _load_full_aggregate(codex_home, verbose)
    recent_sessions = _load_recent_sessions(codex_home, limit)
    typer.echo(json.dumps(_aggregate_to_json(aggregate, recent_sessions), indent=2, sort_keys=True))


def _show_summary(codex_home: Path | None, limit: int, verbose: bool) -> None:
    aggregate = _load_full_aggregate(codex_home, verbose)
    console.print(render_summary(aggregate, limit=limit, width=console.size.width))


def _load_recent_sessions(codex_home: Path | None, limit: int) -> list[SessionMetrics]:
    return parse_session_files(scan_session_files(codex_home), limit=limit)


def _load_all_sessions(codex_home: Path | None) -> list[SessionMetrics]:
    return parse_session_files(scan_session_files(codex_home), limit=None)


def _load_full_aggregate(codex_home: Path | None, verbose: bool) -> AggregateMetrics:
    sessions = _load_all_sessions(codex_home)
    if not verbose:
        for session in sessions:
            session.warnings = []
    return aggregate_sessions(sessions)


def _usage_to_json(usage: TokenUsage | None) -> dict[str, int] | None:
    if usage is None:
        return None
    return {
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "non_cached_input_tokens": usage.non_cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_output_tokens": usage.reasoning_output_tokens,
        "total_tokens": usage.total_tokens,
    }


def _session_to_json(session: SessionMetrics) -> dict[str, object]:
    usage = session.usage or TokenUsage()
    rate = cache_hit_rate(session.usage)
    return {
        "file": session.file_path.name,
        "last_modified": session.last_modified.isoformat(),
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "non_cached_input_tokens": usage.non_cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_output_tokens": usage.reasoning_output_tokens,
        "total_tokens": usage.total_tokens,
        "cache_hit_rate": rate,
        "status": cache_status(rate) if session.usage else "SKIPPED",
        "skipped_reason": session.skipped_reason,
    }


def _aggregate_to_json(aggregate: AggregateMetrics, sessions: list[SessionMetrics]) -> dict[str, object]:
    rate = cache_hit_rate(aggregate.usage)
    return {
        "summary": {
            **(_usage_to_json(aggregate.usage) or {}),
            "cache_hit_rate": rate,
            "status": cache_status(rate),
            "parsed_sessions": aggregate.parsed_sessions,
            "skipped_sessions": aggregate.skipped_sessions,
        },
        "sessions": [_session_to_json(session) for session in sessions],
        "warnings": warning_messages(aggregate),
    }


if __name__ == "__main__":
    app()

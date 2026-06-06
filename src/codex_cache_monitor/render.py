from __future__ import annotations

from datetime import datetime
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .metrics import cache_hit_rate, cache_status, warning_messages
from .models import AggregateMetrics, DoctorReport, SessionMetrics


def format_int(value: int) -> str:
    return f"{value:,}"


def format_compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def format_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def layout_mode(width: int | None) -> str:
    width = width or 120
    if width < 80:
        return "compact"
    if width < 120:
        return "normal"
    return "full"


def render_summary(aggregate: AggregateMetrics, limit: int = 10, width: int | None = None) -> Group:
    mode = layout_mode(width)
    parts = [
        _summary_panel(aggregate, mode=mode),
        _summary_sessions_panel(aggregate.sessions[:limit], mode=mode),
    ]
    if warning_messages(aggregate):
        parts.append(_warnings_panel(aggregate))
    return Group(*parts)


def render_sessions(sessions: list[SessionMetrics], width: int | None = None) -> Panel:
    return _sessions_panel(sessions, mode=layout_mode(width), title="Sessions")


def render_doctor(report: DoctorReport) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Codex home", str(report.codex_home))
    table.add_row("Sessions path", str(report.sessions_path))
    table.add_row("Sessions path exists", "yes" if report.sessions_path_exists else "no")
    table.add_row("JSONL files", format_int(report.jsonl_files))
    table.add_row("Files with usage", format_int(report.usage_files))
    table.add_row("Skipped files", format_int(report.skipped_files))
    table.add_row("Recent session", _format_datetime(report.recent_session_time))

    hints = "\n".join(f"- {hint}" for hint in report.hints) if report.hints else "No issues detected."
    return Panel(Group(table, Text(""), Text(hints)), title="Codex Cache Doctor", box=box.ROUNDED)


def _summary_panel(aggregate: AggregateMetrics, mode: str) -> Panel:
    usage = aggregate.usage
    rate = cache_hit_rate(usage)
    status = cache_status(rate)
    bar_width = {"compact": 18, "normal": 30, "full": 40}[mode]
    lines: list[Text | str] = [
        Text("Cache Hit Rate", style="bold"),
        build_progress_line(rate, status, bar_width),
        "",
    ]

    if mode == "compact":
        metric_rows = [
            ("Input", format_compact_number(usage.input_tokens)),
            ("Cached", format_compact_number(usage.cached_input_tokens)),
            ("Non-cached", format_compact_number(usage.non_cached_input_tokens)),
            ("Output", format_compact_number(usage.output_tokens)),
            ("Sessions", f"{aggregate.parsed_sessions} ok / {aggregate.skipped_sessions} skipped"),
        ]
        label_width = 12
    else:
        metric_rows = [
            ("Input Tokens", format_int(usage.input_tokens)),
            ("Cached Input", format_int(usage.cached_input_tokens)),
            ("Non-cached Input", format_int(usage.non_cached_input_tokens)),
            ("Output Tokens", format_int(usage.output_tokens)),
            ("Reasoning Tokens", format_int(usage.reasoning_output_tokens)),
            ("Total Tokens", format_int(usage.total_tokens)),
            ("Parsed Sessions", format_int(aggregate.parsed_sessions)),
            ("Skipped Sessions", format_int(aggregate.skipped_sessions)),
        ]
        label_width = 18

    value_width = max(len(value) for _, value in metric_rows)
    for label, value in metric_rows:
        lines.append(f"{label:<{label_width}} {value:>{value_width}}")

    return Panel(Group(*lines), title="Codex Cache Monitor", box=box.ROUNDED)


def _summary_sessions_panel(sessions: list[SessionMetrics], mode: str) -> Panel | Group:
    if mode == "compact":
        lines: list[str] = ["Recent"]
        if not sessions:
            lines.append("-")
        for session in sessions[:5]:
            if session.usage is None:
                lines.append(f"{_format_short_datetime(session.last_modified)}  SKIPPED  -")
                continue
            rate = cache_hit_rate(session.usage)
            lines.append(
                f"{_format_short_datetime(session.last_modified)}  {cache_status(rate):<6}  {format_rate(rate):>6}"
            )
        return Group(*(Text(line) for line in lines))

    table = Table(box=box.SIMPLE_HEAVY, expand=False, show_lines=False)
    table.add_column("Time", no_wrap=True)
    table.add_column("Input", justify="right", no_wrap=True)
    table.add_column("Cached", justify="right", no_wrap=True)
    if mode == "full":
        table.add_column("Non-cached", justify="right", no_wrap=True)
        table.add_column("Output", justify="right", no_wrap=True)
    table.add_column("Hit Rate", justify="right", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    if not sessions:
        row = ["-", "-", "-"]
        if mode == "full":
            row.extend(["-", "-"])
        row.extend(["-", "LOW"])
        table.add_row(*row)
        return Panel(table, title="Recent Sessions", box=box.ROUNDED)

    for session in sessions:
        if session.usage is None:
            row = [_format_short_datetime(session.last_modified), "-", "-"]
            if mode == "full":
                row.extend(["-", "-"])
            row.extend(["-", "SKIPPED"])
            table.add_row(*row)
            continue
        rate = cache_hit_rate(session.usage)
        status = cache_status(rate)
        warning = " !" if status == "LOW" else ""
        row = [
            _format_short_datetime(session.last_modified),
            format_compact_number(session.usage.input_tokens),
            format_compact_number(session.usage.cached_input_tokens),
        ]
        if mode == "full":
            row.extend(
                [
                    format_compact_number(session.usage.non_cached_input_tokens),
                    format_compact_number(session.usage.output_tokens),
                ]
            )
        row.extend([f"{format_rate(rate)}{warning}", status])
        table.add_row(*row)

    return Panel(table, title="Recent Sessions", box=box.ROUNDED)


def _sessions_panel(
    sessions: list[SessionMetrics], mode: str, title: str = "Sessions"
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True, show_lines=False)

    if mode == "compact":
        table.add_column("Last Activity", no_wrap=True)
        table.add_column("Input", justify="right", no_wrap=True)
        table.add_column("Hit Rate", justify="right", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        for session in sessions:
            if session.usage is None:
                table.add_row(_format_short_datetime(session.last_modified), "-", "-", "SKIPPED")
                continue
            rate = cache_hit_rate(session.usage)
            table.add_row(
                _format_short_datetime(session.last_modified),
                format_compact_number(session.usage.input_tokens),
                format_rate(rate),
                cache_status(rate),
            )
        return Panel(table, title=title, box=box.ROUNDED)

    if mode == "full":
        table = Table(box=box.SIMPLE_HEAVY, expand=True, show_lines=False)
        table.add_column("Time", no_wrap=True, max_width=11)
        table.add_column("File", overflow="ellipsis", no_wrap=True, max_width=24)
        table.add_column("In", justify="right", no_wrap=True, max_width=6)
        table.add_column("Cache", justify="right", no_wrap=True, max_width=6)
        table.add_column("Non", justify="right", no_wrap=True, max_width=7)
        table.add_column("Out", justify="right", no_wrap=True, max_width=6)
        table.add_column("Reason", justify="right", no_wrap=True, max_width=6)
        table.add_column("Hit", justify="right", no_wrap=True, max_width=8)
        table.add_column("Status", no_wrap=True, max_width=6)
        table.add_column("Skip", overflow="ellipsis", no_wrap=True, max_width=12)
    else:
        table.add_column("Last Activity", no_wrap=True)
        table.add_column("Input", justify="right", no_wrap=True)
        table.add_column("Cached", justify="right", no_wrap=True)
        table.add_column("Non-cached", justify="right", no_wrap=True)
        table.add_column("Hit Rate", justify="right", no_wrap=True)
        table.add_column("Status", no_wrap=True)

    if not sessions:
        row = ["-", "-", "-"]
        if mode == "normal":
            row.append("-")
        if mode == "full":
            row.extend(["-", "-", "-", "-"])
        row.extend(["-", "LOW"])
        if mode == "full":
            row.append("no sessions found")
        table.add_row(*row)
        return Panel(table, title=title, box=box.ROUNDED)

    for session in sessions:
        if session.usage is None:
            if mode == "full":
                row = [
                    _format_short_datetime(session.last_modified),
                    _truncate(session.file_path.name, 24),
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "SKIPPED",
                    _truncate(session.skipped_reason or "skipped", 12),
                ]
            else:
                row = [_format_datetime(session.last_modified), "-", "-"]
                if mode == "normal":
                    row.append("-")
                row.extend(["-", "SKIPPED"])
            table.add_row(*row)
            continue

        rate = cache_hit_rate(session.usage)
        status = cache_status(rate)
        warning = " !" if status == "LOW" else ""
        row = [
            _format_short_datetime(session.last_modified) if mode == "full" else _format_datetime(session.last_modified),
        ]
        if mode == "full":
            row.append(_truncate(session.file_path.name, 24))
        row.extend(
            [
                format_compact_number(session.usage.input_tokens),
                format_compact_number(session.usage.cached_input_tokens),
            ]
        )
        if mode == "normal":
            row.append(format_compact_number(session.usage.non_cached_input_tokens))
        if mode == "full":
            row.extend(
                [
                    format_compact_number(session.usage.non_cached_input_tokens),
                    format_compact_number(session.usage.output_tokens),
                    format_compact_number(session.usage.reasoning_output_tokens),
                ]
            )
        row.extend(
            [
                f"{format_rate(rate)}{warning}",
                status,
            ]
        )
        if mode == "full":
            row.append(_truncate(session.skipped_reason or "", 12))
        table.add_row(*row)

    return Panel(table, title=title, box=box.ROUNDED)


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def _format_short_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%m-%d %H:%M")


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


def build_progress_line(rate: float, status: str, width: int) -> Text:
    filled = max(0, min(width, int(width * rate)))
    empty = width - filled
    text = Text()
    text.append("█" * filled, style="magenta")
    text.append("░" * empty, style="dim")
    text.append(f" {format_rate(rate)} ", style="bold")
    text.append(status, style=_status_style(status))
    return text


def _status_style(status: str) -> str:
    return {"GOOD": "bold green", "NORMAL": "bold yellow", "LOW": "bold red"}.get(status, "bold")


def _warnings_panel(aggregate: AggregateMetrics) -> Panel:
    messages = warning_messages(aggregate)
    if len(messages) > 5:
        messages = [*messages[:5], f"... and {len(messages) - 5} more warning(s)"]
    return Panel("\n".join(messages), title="Warnings", box=box.ROUNDED)

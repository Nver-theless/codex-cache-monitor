from __future__ import annotations

from .models import AggregateMetrics, SessionMetrics, TokenUsage


def cache_hit_rate(usage: TokenUsage | None) -> float:
    if usage is None or usage.input_tokens <= 0:
        return 0.0
    return usage.cached_input_tokens / usage.input_tokens


def cache_status(rate: float) -> str:
    if rate >= 0.7:
        return "GOOD"
    if rate >= 0.3:
        return "NORMAL"
    return "LOW"


def aggregate_sessions(sessions: list[SessionMetrics]) -> AggregateMetrics:
    total = TokenUsage()
    warnings: list[str] = []
    parsed = 0
    skipped = 0

    for session in sessions:
        warnings.extend(session.warnings)
        if session.is_skipped or session.usage is None:
            skipped += 1
            continue

        parsed += 1
        total.input_tokens += session.usage.input_tokens
        total.cached_input_tokens += session.usage.cached_input_tokens
        total.output_tokens += session.usage.output_tokens
        total.reasoning_output_tokens += session.usage.reasoning_output_tokens
        total.total_tokens += session.usage.total_tokens

    return AggregateMetrics(
        usage=total,
        parsed_sessions=parsed,
        skipped_sessions=skipped,
        sessions=sessions,
        warnings=warnings,
    )


def warning_messages(aggregate: AggregateMetrics) -> list[str]:
    messages: list[str] = []
    if aggregate.skipped_sessions:
        noun = "session" if aggregate.skipped_sessions == 1 else "sessions"
        messages.append(
            f"{aggregate.skipped_sessions} {noun} skipped because usage data was missing or incomplete"
        )
    if aggregate.parsed_sessions == 0:
        messages.append("No token usage found. Codex CLI may be old or the log format may be unsupported.")
    messages.extend(aggregate.warnings)
    return messages

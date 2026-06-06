from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import SessionMetrics, TokenUsage
from .scanner import file_mtime

USAGE_KEYS = {
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
}


def parse_session_file(path: Path) -> SessionMetrics:
    warnings: list[str] = []
    total_usage: TokenUsage | None = None
    fallback_usage: TokenUsage | None = None

    try:
        last_modified = file_mtime(path)
    except OSError:
        last_modified = datetime.fromtimestamp(0)

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    warnings.append(f"{path.name}:{line_number}: invalid JSON skipped ({exc.msg})")
                    continue

                for candidate, is_total in _iter_usage_candidates(item):
                    usage = _usage_from_mapping(candidate)
                    if usage is None:
                        continue
                    fallback_usage = usage
                    if is_total:
                        total_usage = usage
    except OSError as exc:
        return SessionMetrics(
            file_path=path,
            last_modified=last_modified,
            usage=None,
            skipped_reason=f"could not read file: {exc}",
            warnings=warnings,
        )

    usage = total_usage or fallback_usage
    if usage is None:
        return SessionMetrics(
            file_path=path,
            last_modified=last_modified,
            usage=None,
            skipped_reason="no token usage found",
            warnings=warnings,
        )

    if usage.input_tokens <= 0:
        return SessionMetrics(
            file_path=path,
            last_modified=last_modified,
            usage=None,
            skipped_reason="missing or zero input tokens",
            warnings=warnings,
        )

    if usage.total_tokens <= 0:
        usage.total_tokens = (
            usage.input_tokens
            + usage.output_tokens
            + usage.reasoning_output_tokens
        )

    return SessionMetrics(file_path=path, last_modified=last_modified, usage=usage, warnings=warnings)


def parse_session_files(paths: list[Path], limit: int | None = None) -> list[SessionMetrics]:
    selected = paths[:limit] if limit and limit > 0 else paths
    return [parse_session_file(path) for path in selected]


def _iter_usage_candidates(value: Any) -> Iterator[tuple[Mapping[str, Any], bool]]:
    if isinstance(value, Mapping):
        direct_keys = USAGE_KEYS.intersection(value.keys())
        if "token_count" in value and isinstance(value["token_count"], Mapping):
            yield value["token_count"], False
        if direct_keys:
            yield value, False

        for key in ("event_msg", "payload", "info"):
            nested = value.get(key)
            if isinstance(nested, str):
                parsed = _maybe_json(nested)
                if parsed is not None:
                    yield from _iter_usage_candidates(parsed)
            elif isinstance(nested, (Mapping, list)):
                yield from _iter_usage_candidates(nested)

        payload = value.get("payload")
        if isinstance(payload, Mapping):
            info = payload.get("info")
            if isinstance(info, Mapping):
                for usage_key, is_total in (
                    ("last_token_usage", False),
                    ("total_token_usage", True),
                ):
                    usage_value = info.get(usage_key)
                    if isinstance(usage_value, Mapping):
                        yield usage_value, is_total
                    elif isinstance(usage_value, str):
                        parsed_usage = _maybe_json(usage_value)
                        if isinstance(parsed_usage, Mapping):
                            yield parsed_usage, is_total

        for child_key, child_value in value.items():
            if child_key in {"token_count", "event_msg", "payload", "info"}:
                continue
            if isinstance(child_value, (Mapping, list)):
                yield from _iter_usage_candidates(child_value)

    elif isinstance(value, list):
        for item in value:
            yield from _iter_usage_candidates(item)


def _maybe_json(value: str) -> Any:
    value = value.strip()
    if not value or value[0] not in "[{":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _usage_from_mapping(value: Mapping[str, Any]) -> TokenUsage | None:
    if not USAGE_KEYS.intersection(value.keys()):
        return None

    extracted = {
        "input_tokens": _int_from_any(value.get("input_tokens")),
        "cached_input_tokens": _int_from_any(value.get("cached_input_tokens")),
        "output_tokens": _int_from_any(value.get("output_tokens")),
        "reasoning_output_tokens": _int_from_any(value.get("reasoning_output_tokens")),
        "total_tokens": _int_from_any(value.get("total_tokens")),
    }

    return TokenUsage(**extracted)


def _int_from_any(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str):
        try:
            return max(int(float(value.replace(",", ""))), 0)
        except ValueError:
            return 0
    return 0

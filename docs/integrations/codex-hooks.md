# Codex Hooks Integration

This is not a native Codex UI plugin.
It is an integration pattern using Codex Hooks and the `codex-cache status` command.

`codex-cache-monitor` keeps Codex log parsing inside the CLI. Other tools should read the generated status file instead of parsing `~/.codex/sessions` directly.

## Recommended Flow

```text
Codex event
  -> codex-cache status --write-state
  -> ~/.codex-cache-monitor/status.json
  -> Raycast / menu bar / other UI refreshes
```

## Hook Command

A hook can call:

```bash
codex-cache status --write-state
```

This writes:

```text
~/.codex-cache-monitor/status.json
```

The file contains metadata-only JSON:

- cache hit rate
- GOOD / NORMAL / LOW status
- input token totals
- cached input token totals
- skipped session count
- update timestamp

It does not contain prompts, responses, tool output, command text, raw JSONL, or file contents.

## Conceptual Example

If your Codex Hooks setup supports running a shell command after an event, use this command as the action:

```bash
codex-cache status --write-state
```

The exact hook configuration format is intentionally not shown here because hook configuration fields may vary. Treat this as a conceptual integration pattern until you have the current official Codex Hooks configuration in front of you.

## Future UI Consumers

Raycast, Alfred, a status bar script, or a future macOS menu bar app can read:

```text
~/.codex-cache-monitor/status.json
```

Those tools should not parse `~/.codex/sessions` themselves. Keeping parsing in `codex-cache-monitor` makes the integration thinner and easier to update if Codex session log formats change.

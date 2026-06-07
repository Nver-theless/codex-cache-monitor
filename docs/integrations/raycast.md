# Raycast Integration

Raycast can call `codex-cache-monitor` through Script Commands. This is a lightweight launcher integration, not a native Raycast extension.

The simplest command is:

```bash
codex-cache status --plain
```

For a more detailed one-line summary, use:

```bash
codex-cache status
```

For future custom scripts, JSON output is available:

```bash
codex-cache status --json
```

All commands read local Codex session metrics through `codex-cache-monitor`. They do not upload logs and do not print prompt, response, tool output, raw JSONL, or file contents.

## Example 1: Compact Mode

File name:

```text
codex-cache-plain.sh
```

Script:

```bash
#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Codex Cache
# @raycast.mode compact
#
# Optional parameters:
# @raycast.icon ⚡
#
# Documentation:
# @raycast.description Show Codex prompt cache hit rate.

codex-cache status --plain
```

## Example 2: Detail Mode

File name:

```text
codex-cache-detail.sh
```

Script:

```bash
#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Codex Cache Detail
# @raycast.mode fullOutput
#
# Optional parameters:
# @raycast.icon 📊
#
# Documentation:
# @raycast.description Show Codex prompt cache summary.

codex-cache status
```

## Installation

1. Open Raycast.
2. Open Script Commands settings.
3. Add a script directory.
4. Save one of the scripts above into that directory.
5. Make the script executable:

```bash
chmod +x script-name.sh
```

6. Run `Codex Cache` in Raycast.

## If Raycast Cannot Find codex-cache

Find the installed command path:

```bash
which codex-cache
```

Then replace the command in the script with the absolute path:

```bash
/path/to/codex-cache status --plain
```

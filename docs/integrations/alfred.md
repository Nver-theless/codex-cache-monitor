# Alfred Integration

Alfred can call `codex-cache-monitor` through a Workflow Run Script action. A future workflow could use Script Filter, but the first version should stay simple and call the `status` command directly.

This is not a packaged `.alfredworkflow` file and does not depend on a custom Alfred API.

## Simplest Run Script

Use this script to show the detailed one-line status:

```bash
#!/bin/bash
codex-cache status
```

Use this script to show only the short status:

```bash
#!/bin/bash
codex-cache status --plain
```

Both commands read local Codex session metrics through `codex-cache-monitor`. They do not upload logs and do not print prompt, response, tool output, raw JSONL, or file contents.

## Setup

1. Open Alfred Preferences.
2. Create a new Workflow.
3. Add a Keyword input, for example `cc`.
4. Add a Run Script action.
5. Set Language to `/bin/bash`.
6. Paste one of the scripts above.
7. Connect the Keyword input to the Run Script action.

## If Alfred Cannot Find codex-cache

Find the installed command path:

```bash
which codex-cache
```

Then replace the command in the script with the absolute path:

```bash
/path/to/codex-cache status --plain
```

## Reading the Status File

Alfred can also read the local status file:

```bash
#!/bin/bash
cat ~/.codex-cache-monitor/status.json
```

For most workflows, directly calling the command is recommended:

```bash
codex-cache status --plain
```

That recalculates the latest status instead of relying on a previously written state file.

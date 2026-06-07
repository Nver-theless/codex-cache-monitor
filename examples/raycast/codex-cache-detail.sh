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

set -euo pipefail

if ! command -v codex-cache >/dev/null 2>&1; then
  echo "codex-cache not found. Install codex-cache-monitor or replace codex-cache with its absolute path."
  exit 1
fi

codex-cache status

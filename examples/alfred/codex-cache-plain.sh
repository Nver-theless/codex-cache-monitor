#!/bin/bash

set -euo pipefail

if ! command -v codex-cache >/dev/null 2>&1; then
  echo "codex-cache not found. Install codex-cache-monitor or replace codex-cache with its absolute path."
  exit 1
fi

codex-cache status --plain

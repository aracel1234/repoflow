#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x "$HOME/.local/share/repoflow/.venv/bin/python" ]]; then
  PY="$HOME/.local/share/repoflow/.venv/bin/python"
else
  PY="python3"
fi

echo "RepoFlow tests using: $PY"
"$PY" -m unittest discover -s tests -v

#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/repoflow"
rm -f "$HOME/.local/bin/repoflow"
rm -f "$HOME/.local/share/applications/repoflow.desktop"
echo "RepoFlow application files removed. Settings remain at ~/.config/repoflow"

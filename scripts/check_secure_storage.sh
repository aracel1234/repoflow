#!/usr/bin/env bash
set -euo pipefail

if ! command -v secret-tool >/dev/null 2>&1; then
  echo "FAIL: secret-tool tidak ditemukan."
  echo "Install di KDE Neon/Ubuntu: sudo apt install libsecret-tools"
  exit 2
fi

echo "secret-tool: $(command -v secret-tool)"
if command -v busctl >/dev/null 2>&1; then
  if busctl --user --list 2>/dev/null | grep -q 'org.freedesktop.secrets'; then
    echo "Secret Service D-Bus name: active"
  else
    echo "Secret Service D-Bus name: not currently listed (it may still be D-Bus activated on demand)"
  fi
fi

probe="repoflow-secure-storage-probe-$$"
attrs=(application repoflow service secure-storage-probe account "$USER")
cleanup() { secret-tool clear "${attrs[@]}" >/dev/null 2>&1 || true; }
trap cleanup EXIT

printf '%s' "$probe" | secret-tool store --label='RepoFlow secure storage probe' "${attrs[@]}"
read_back="$(secret-tool lookup "${attrs[@]}" || true)"
if [ "$read_back" != "$probe" ]; then
  echo "FAIL: secret berhasil ditulis tetapi hasil lookup tidak cocok."
  exit 3
fi

echo "PASS: Secret Service store + lookup + clear bekerja."

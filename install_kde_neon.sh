#!/usr/bin/env bash
set -euo pipefail
APP_NAME="RepoFlow"
APP_DIR="${HOME}/.local/share/repoflow"
VENV_DIR="${APP_DIR}/.venv"
DESKTOP_DIR="${HOME}/.local/share/applications"
BIN_DIR="${HOME}/.local/bin"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/repoflow"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: Git belum terpasang. Instal dulu: sudo apt install git"
  exit 1
fi

# Optional but strongly recommended: secure GitHub token persistence.
if ! command -v secret-tool >/dev/null 2>&1; then
  echo
  echo "RepoFlow: 'secret-tool' belum tersedia."
  echo "Fitur Remember GitHub Token memerlukan paket libsecret-tools pada KDE Neon/Ubuntu."
  if command -v apt-get >/dev/null 2>&1 && [ -t 0 ]; then
    read -r -p "Install libsecret-tools sekarang? [Y/n] " answer
    answer="${answer:-Y}"
    case "$answer" in
      [Yy]*)
        if sudo apt-get install -y libsecret-tools; then
          echo "RepoFlow: libsecret-tools berhasil dipasang."
        else
          echo "WARNING: libsecret-tools gagal dipasang. RepoFlow tetap dapat berjalan, tetapi token GitHub hanya akan disimpan selama sesi aplikasi."
        fi
        ;;
      *)
        echo "RepoFlow: melewati instalasi libsecret-tools. Token GitHub akan session-only sampai helper tersebut tersedia."
        ;;
    esac
  else
    echo "Install manual jika ingin penyimpanan token aman: sudo apt install libsecret-tools"
  fi
fi

if [ -x /usr/bin/python3 ]; then
  SYSTEM_PYTHON=/usr/bin/python3
else
  SYSTEM_PYTHON="$(command -v python3 || true)"
fi
if [ -z "${SYSTEM_PYTHON}" ] || [ ! -x "${SYSTEM_PYTHON}" ]; then
  echo "ERROR: system python3 belum tersedia."
  exit 1
fi

mkdir -p "$APP_DIR" "$DESKTOP_DIR" "$BIN_DIR" "$STATE_DIR"
rm -rf "$APP_DIR/repoflow"
cp -R "$SOURCE_DIR/repoflow" "$APP_DIR/"
find "$APP_DIR/repoflow" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
cp "$SOURCE_DIR/requirements.txt" "$APP_DIR/"

SYSTEM_BASE="$($SYSTEM_PYTHON -c 'import sys; print(sys.base_prefix)')"
if [ -x "$VENV_DIR/bin/python" ]; then
  VENV_BASE="$($VENV_DIR/bin/python -c 'import sys; print(sys.base_prefix)' 2>/dev/null || true)"
  if [ "$VENV_BASE" != "$SYSTEM_BASE" ]; then
    echo "RepoFlow: virtual environment lama memakai Python non-system: ${VENV_BASE:-unknown}"
    echo "RepoFlow: membuat ulang environment dengan $SYSTEM_PYTHON (base: $SYSTEM_BASE)"
    rm -rf "$VENV_DIR"
  fi
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  if ! "$SYSTEM_PYTHON" -m venv "$VENV_DIR" 2>/dev/null; then
    echo "ERROR: modul venv untuk system Python belum tersedia."
    echo "Jalankan: sudo apt install python3-venv"
    exit 1
  fi
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

cat > "$BIN_DIR/repoflow" <<LAUNCHER
#!/usr/bin/env bash
APP_DIR="$APP_DIR"
STATE_DIR="$STATE_DIR"
LOG_FILE="\$STATE_DIR/repoflow.log"
mkdir -p "\$STATE_DIR"
cd "\$APP_DIR" || exit 1
unset PYTHONHOME PYTHONPATH QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QML2_IMPORT_PATH
export PATH="/usr/local/bin:/usr/bin:/bin:\${PATH:-}"
{
  echo
  echo "===== RepoFlow start \$(date --iso-8601=seconds 2>/dev/null || date) ====="
  echo "launcher_python=\$APP_DIR/.venv/bin/python"
  "\$APP_DIR/.venv/bin/python" -c 'import sys; print("python_executable=" + sys.executable); print("python_version=" + sys.version.split()[0]); print("python_base_prefix=" + sys.base_prefix)' || true
} >>"\$LOG_FILE" 2>&1
"\$APP_DIR/.venv/bin/python" -m repoflow.main "\$@" >>"\$LOG_FILE" 2>&1
status=\$?
echo "RepoFlow exit_status=\$status" >>"\$LOG_FILE"
if [ \$status -ne 0 ] && command -v kdialog >/dev/null 2>&1; then
  kdialog --error "RepoFlow berhenti tidak normal. Log tersimpan di:\n\$LOG_FILE"
fi
exit \$status
LAUNCHER
chmod +x "$BIN_DIR/repoflow"

cat > "$DESKTOP_DIR/repoflow.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=RepoFlow
Comment=Lightweight Git desktop client
Exec=$BIN_DIR/repoflow
TryExec=$BIN_DIR/repoflow
Path=$APP_DIR
Terminal=false
Categories=Development;RevisionControl;
StartupNotify=true
DESKTOP
chmod +x "$DESKTOP_DIR/repoflow.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 >/dev/null 2>&1 || true
fi

echo
echo "RepoFlow v0.2.7 terpasang."
echo "Python runtime: $($VENV_DIR/bin/python -c 'import sys; print(sys.executable + " | " + sys.version.split()[0] + " | base=" + sys.base_prefix)')"
echo "Log diagnostik: $STATE_DIR/repoflow.log"
if command -v secret-tool >/dev/null 2>&1; then
  echo "Secure credential helper: $(command -v secret-tool)"
else
  echo "Secure credential helper: unavailable (GitHub token persistence will be session-only)"
fi
echo "Cari 'RepoFlow' di Application Launcher KDE."

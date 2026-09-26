from __future__ import annotations

import faulthandler
import logging
import os
from pathlib import Path
import sys

import PySide6
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication, QMessageBox

from repoflow.services.git_service import GitService
from repoflow.ui.main_window import MainWindow
from repoflow.ui.theme import APP_STYLE

_FAULT_HANDLE = None


def _state_dir() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    path = root / "repoflow"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _configure_diagnostics() -> None:
    global _FAULT_HANDLE
    log_path = _state_dir() / "repoflow.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    _FAULT_HANDLE = log_path.open("a", encoding="utf-8", buffering=1)
    faulthandler.enable(file=_FAULT_HANDLE, all_threads=True)

    def exception_hook(exc_type, exc_value, exc_tb):
        logging.getLogger("repoflow").critical(
            "Unhandled Python exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = exception_hook
    logging.getLogger("repoflow").info(
        "Startup python=%s version=%s base_prefix=%s PySide6=%s Qt=%s",
        sys.executable,
        sys.version.split()[0],
        sys.base_prefix,
        PySide6.__version__,
        qVersion(),
    )


def main() -> int:
    _configure_diagnostics()
    app = QApplication(sys.argv)
    app.setApplicationName("RepoFlow")
    app.setOrganizationName("RepoFlow")
    app.setStyleSheet(APP_STYLE)

    if not GitService.git_available():
        QMessageBox.critical(
            None,
            "RepoFlow",
            "Git was not found. Install Git first, then reopen RepoFlow.",
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

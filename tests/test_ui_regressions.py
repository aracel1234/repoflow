from __future__ import annotations

import unittest
from pathlib import Path


class UIRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.main_window = (self.root / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.installer = (self.root / "install_kde_neon.sh").read_text(encoding="utf-8")

    def test_commit_and_push_has_no_qt_mnemonic_ampersand(self) -> None:
        self.assertIn('QPushButton("Commit and Push")', self.main_window)
        self.assertNotIn('QPushButton("Commit & Push")', self.main_window)

    def test_background_finish_does_not_overwrite_result_with_ready(self) -> None:
        self.assertIn('self._set_busy(False, None)', self.main_window)
        self.assertNotIn('self._set_busy(False, "Ready")', self.main_window)

    def test_installer_registers_application_icon(self) -> None:
        self.assertIn('Icon=$APP_DIR/assets/repoflow.svg', self.installer)
        self.assertTrue((self.root / "assets" / "repoflow.svg").is_file())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path


class Stage3UIRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.main = (root / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.dialogs = (root / "repoflow" / "ui" / "dialogs.py").read_text(encoding="utf-8")

    def test_gitignore_manager_is_exposed_in_repository_menu(self) -> None:
        self.assertIn('QAction("Manage .gitignore…", self)', self.main)
        self.assertIn("class GitIgnoreDialog", self.dialogs)

    def test_diverged_or_conflicted_repo_blocks_pull_and_push(self) -> None:
        self.assertIn("and not conflicts and not diverged", self.main)
        self.assertIn("self.pull_button.setEnabled(available and self._can_pull)", self.main)
        self.assertIn("self.push_button.setEnabled(available and self._can_push)", self.main)
        self.assertIn("if self._current_diverged:", self.main)
        self.assertIn("available and not self._current_conflicts and not self._current_diverged", self.main)

    def test_safety_warning_is_used_before_staging(self) -> None:
        self.assertIn("SafetyWarningDialog", self.main)
        self.assertIn("allow_ignore=entry.untracked", self.main)
        self.assertIn("SafetyScanner.exact_gitignore_pattern(path)", self.main)
        self.assertIn('status_text += " · ⚠ Review"', self.main)


if __name__ == "__main__":
    unittest.main()

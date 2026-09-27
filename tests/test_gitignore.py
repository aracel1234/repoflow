from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class GitIgnoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-ignore-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True, text=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_read_write_and_append_gitignore_without_duplicates(self) -> None:
        self.assertEqual(self.git.read_gitignore(), "")
        self.git.write_gitignore(".venv/\n")
        added = self.git.append_gitignore_patterns(["/.env", ".venv/", "/private\\ file.key"])
        self.assertEqual(added, ["/.env", "/private\\ file.key"])
        text = self.git.read_gitignore()
        self.assertIn(".venv/\n", text)
        self.assertIn("/.env\n", text)
        self.assertEqual(text.count(".venv/"), 1)

    def test_is_tracked_distinguishes_tracked_and_untracked(self) -> None:
        (self.root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.root, check=True)
        self.assertTrue(self.git.is_tracked("tracked.txt"))
        self.assertFalse(self.git.is_tracked("untracked.txt"))


if __name__ == "__main__":
    unittest.main()

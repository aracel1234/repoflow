from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class HunkStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Tests"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=self.root, check=True)
        self.file = self.root / "notes.txt"
        self.file.write_text("".join(f"line {i}\n" for i in range(1, 31)), encoding="utf-8")
        subprocess.run(["git", "add", "notes.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_stage_one_of_two_hunks_creates_partial_state(self) -> None:
        lines = self.file.read_text(encoding="utf-8").splitlines()
        lines[1] = "line 2 changed A"
        lines[24] = "line 25 changed B"
        self.file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        hunks = self.git.unstaged_hunks("notes.txt")
        self.assertEqual(2, len(hunks))
        self.git.stage_hunks("notes.txt", [0])

        entry = next(item for item in self.git.status() if item.path == "notes.txt")
        self.assertTrue(entry.partially_staged)
        staged = self.git.staged_diff("notes.txt")
        unstaged = self.git.diff("notes.txt")
        self.assertIn("line 2 changed A", staged)
        self.assertNotIn("line 25 changed B", staged)
        self.assertIn("line 25 changed B", unstaged)
        self.assertNotIn("line 2 changed A", unstaged)

    def test_untracked_file_has_no_hunk_staging(self) -> None:
        (self.root / "new.txt").write_text("hello\n", encoding="utf-8")
        self.assertEqual([], self.git.unstaged_hunks("new.txt"))


if __name__ == "__main__":
    unittest.main()

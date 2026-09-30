from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class StashWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Tests"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=self.root, check=True)
        (self.root / "tracked.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_apply_and_drop_stash_with_untracked_file(self) -> None:
        (self.root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("new\n", encoding="utf-8")

        message = self.git.stash_create("qa stash", include_untracked=True)
        self.assertIn("Saved working directory", message)
        self.assertEqual([], self.git.status())

        stashes = self.git.stash_list()
        self.assertEqual(1, len(stashes))
        self.assertIn("qa stash", stashes[0].subject)

        self.git.stash_apply(stashes[0].ref)
        paths = {entry.path for entry in self.git.status()}
        self.assertIn("tracked.txt", paths)
        self.assertIn("untracked.txt", paths)
        self.assertEqual(1, len(self.git.stash_list()))

        self.git.stash_drop(stashes[0].ref)
        self.assertEqual([], self.git.stash_list())


if __name__ == "__main__":
    unittest.main()

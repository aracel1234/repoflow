from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitError, GitService


class BranchManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Tests"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_rename_and_safe_delete_merged_branch(self) -> None:
        self.git.create_branch("feature/old", switch=False)
        self.git.rename_branch("feature/old", "feature/new")
        self.assertIn("feature/new", self.git.local_branches())
        self.assertNotIn("feature/old", self.git.local_branches())
        self.git.delete_branch("feature/new")
        self.assertNotIn("feature/new", self.git.local_branches())

    def test_safe_delete_refuses_unmerged_branch(self) -> None:
        self.git.create_branch("feature/work", switch=True)
        (self.root / "work.txt").write_text("work\n", encoding="utf-8")
        subprocess.run(["git", "add", "work.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "unmerged"], cwd=self.root, check=True, capture_output=True)
        self.git.switch_branch("main")
        with self.assertRaises(GitError):
            self.git.delete_branch("feature/work")
        self.assertIn("feature/work", self.git.local_branches())


if __name__ == "__main__":
    unittest.main()

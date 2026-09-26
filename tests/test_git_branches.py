from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitError, GitService


class BranchWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-branch-test-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "repoflow-test@example.invalid"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("RepoFlow branch test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.root, check=True, capture_output=True, text=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_and_switch_branch(self) -> None:
        self.git.create_branch("feature/qa-test", switch=True)
        self.assertEqual(self.git.branch(), "feature/qa-test")
        self.assertIn("feature/qa-test", self.git.local_branches())

    def test_create_without_switch_keeps_current_branch(self) -> None:
        self.git.create_branch("feature/background", switch=False)
        self.assertEqual(self.git.branch(), "main")
        self.assertIn("feature/background", self.git.local_branches())

    def test_switch_existing_branch(self) -> None:
        self.git.create_branch("feature/qa-test", switch=False)
        self.git.switch_branch("feature/qa-test")
        self.assertEqual(self.git.branch(), "feature/qa-test")
        self.git.switch_branch("main")
        self.assertEqual(self.git.branch(), "main")

    def test_invalid_branch_name_is_rejected(self) -> None:
        with self.assertRaises(GitError):
            self.git.create_branch("bad branch name", switch=True)

    def test_duplicate_branch_is_rejected(self) -> None:
        self.git.create_branch("feature/qa-test", switch=False)
        with self.assertRaises(GitError):
            self.git.create_branch("feature/qa-test", switch=True)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class PartialStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-test-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "repoflow-test@example.invalid"], cwd=self.root, check=True)
        self.readme = self.root / "README.md"
        self.readme.write_text("RepoFlow QA\nTesting modified file\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.root, check=True, capture_output=True, text=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _readme_status(self):
        return next(item for item in self.git.status() if item.path == "README.md")

    def test_partial_staging_is_detected_and_diffs_are_separate(self) -> None:
        self.readme.write_text("RepoFlow QA\nTesting modified file\nVERSION A\n", encoding="utf-8")
        self.git.stage(["README.md"])

        staged_only = self._readme_status()
        self.assertTrue(staged_only.fully_staged)
        self.assertFalse(staged_only.partially_staged)

        self.readme.write_text(
            "RepoFlow QA\nTesting modified file\nVERSION A\nVERSION B\n",
            encoding="utf-8",
        )

        partial = self._readme_status()
        self.assertTrue(partial.staged)
        self.assertTrue(partial.unstaged)
        self.assertTrue(partial.partially_staged)
        self.assertEqual(partial.index_status, "M")
        self.assertEqual(partial.worktree_status, "M")

        staged_diff = self.git.staged_diff("README.md")
        unstaged_diff = self.git.diff("README.md")
        self.assertIn("+VERSION A", staged_diff)
        self.assertNotIn("+VERSION B", staged_diff)
        self.assertIn("+VERSION B", unstaged_diff)

    def test_stage_again_promotes_partial_file_to_fully_staged(self) -> None:
        self.readme.write_text("RepoFlow QA\nTesting modified file\nVERSION A\n", encoding="utf-8")
        self.git.stage(["README.md"])
        self.readme.write_text(
            "RepoFlow QA\nTesting modified file\nVERSION A\nVERSION B\n",
            encoding="utf-8",
        )
        self.assertTrue(self._readme_status().partially_staged)

        self.git.stage(["README.md"])
        state = self._readme_status()
        self.assertTrue(state.fully_staged)
        self.assertFalse(state.unstaged)
        self.assertIn("+VERSION B", self.git.staged_diff("README.md"))

    def test_unstage_partial_file_moves_all_changes_to_worktree(self) -> None:
        self.readme.write_text("RepoFlow QA\nTesting modified file\nVERSION A\n", encoding="utf-8")
        self.git.stage(["README.md"])
        self.readme.write_text(
            "RepoFlow QA\nTesting modified file\nVERSION A\nVERSION B\n",
            encoding="utf-8",
        )
        self.assertTrue(self._readme_status().partially_staged)

        self.git.unstage(["README.md"])
        state = self._readme_status()
        self.assertFalse(state.staged)
        self.assertTrue(state.unstaged)
        diff = self.git.diff("README.md")
        self.assertIn("+VERSION A", diff)
        self.assertIn("+VERSION B", diff)


if __name__ == "__main__":
    unittest.main()

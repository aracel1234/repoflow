from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitError, GitService


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def configure(path: Path) -> None:
    git(path, "config", "user.name", "RepoFlow Test")
    git(path, "config", "user.email", "repoflow-test@example.invalid")


class HistoryRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-history-")
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-b", "main")
        configure(self.root)
        (self.root / "notes.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "notes.txt")
        git(self.root, "commit", "-m", "base")
        self.service = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_commit_detail_reports_metadata_files_and_patch(self) -> None:
        (self.root / "notes.txt").write_text("base\nsecond\n", encoding="utf-8")
        git(self.root, "commit", "-am", "add second line")
        sha = git(self.root, "rev-parse", "HEAD").stdout.strip()
        detail = self.service.commit_detail(sha)
        self.assertEqual(detail.sha, sha)
        self.assertEqual(detail.subject, "add second line")
        self.assertTrue(any("notes.txt" in entry for entry in detail.files))
        self.assertIn("+second", detail.patch)
        self.assertEqual(detail.parent_count, 1)

    def test_revert_commit_creates_new_commit_without_rewriting_history(self) -> None:
        (self.root / "notes.txt").write_text("changed\n", encoding="utf-8")
        git(self.root, "commit", "-am", "change notes")
        target = git(self.root, "rev-parse", "HEAD").stdout.strip()
        before_count = int(git(self.root, "rev-list", "--count", "HEAD").stdout.strip())
        self.service.revert_commit(target)
        after_count = int(git(self.root, "rev-list", "--count", "HEAD").stdout.strip())
        self.assertEqual(after_count, before_count + 1)
        self.assertEqual((self.root / "notes.txt").read_text(encoding="utf-8"), "base\n")
        self.assertIn("Revert", git(self.root, "log", "-1", "--pretty=%s").stdout)

    def test_revert_merge_commit_is_refused_without_mainline_choice(self) -> None:
        git(self.root, "switch", "-c", "feature")
        (self.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        git(self.root, "add", "feature.txt")
        git(self.root, "commit", "-m", "feature work")
        git(self.root, "switch", "main")
        (self.root / "main.txt").write_text("main\n", encoding="utf-8")
        git(self.root, "add", "main.txt")
        git(self.root, "commit", "-m", "main work")
        git(self.root, "merge", "--no-ff", "feature", "-m", "merge feature")
        sha = git(self.root, "rev-parse", "HEAD").stdout.strip()
        with self.assertRaisesRegex(GitError, "mainline"):
            self.service.revert_commit(sha)

    def test_history_can_include_other_local_branches_for_cherry_pick_selection(self) -> None:
        git(self.root, "switch", "-c", "feature/history")
        (self.root / "branch.txt").write_text("branch only\n", encoding="utf-8")
        git(self.root, "add", "branch.txt")
        git(self.root, "commit", "-m", "branch-only commit")
        git(self.root, "switch", "main")
        current_subjects = [item.subject for item in self.service.history()]
        all_subjects = [item.subject for item in self.service.history(all_local_branches=True)]
        self.assertNotIn("branch-only commit", current_subjects)
        self.assertIn("branch-only commit", all_subjects)

    def test_cherry_pick_clean_commit(self) -> None:
        git(self.root, "switch", "-c", "feature")
        (self.root / "feature.txt").write_text("picked\n", encoding="utf-8")
        git(self.root, "add", "feature.txt")
        git(self.root, "commit", "-m", "feature commit")
        target = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "main")
        self.service.cherry_pick_commit(target)
        self.assertEqual((self.root / "feature.txt").read_text(encoding="utf-8"), "picked\n")
        self.assertEqual(git(self.root, "log", "-1", "--pretty=%s").stdout.strip(), "feature commit")

    def test_cherry_pick_conflict_is_preserved_and_abort_restores_state(self) -> None:
        git(self.root, "switch", "-c", "feature")
        (self.root / "notes.txt").write_text("feature\n", encoding="utf-8")
        git(self.root, "commit", "-am", "feature conflict")
        target = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "main")
        (self.root / "notes.txt").write_text("main\n", encoding="utf-8")
        git(self.root, "commit", "-am", "main conflict")
        with self.assertRaisesRegex(GitError, "paused"):
            self.service.cherry_pick_commit(target)
        self.assertEqual(self.service.operation_state(), "cherry-pick")
        self.assertTrue(self.service.conflicted_files())
        self.service.abort_current_operation()
        self.assertIsNone(self.service.operation_state())
        self.assertFalse(self.service.conflicted_files())
        self.assertEqual((self.root / "notes.txt").read_text(encoding="utf-8"), "main\n")


if __name__ == "__main__":
    unittest.main()

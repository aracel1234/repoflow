from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def configure(path: Path) -> None:
    git(path, "config", "user.name", "RepoFlow Test")
    git(path, "config", "user.email", "repoflow-test@example.invalid")


class RemoteBranchTagSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-remote-tools-")
        self.base = Path(self.tmp.name)
        self.remote = self.base / "remote.git"
        self.local = self.base / "local"
        self.other = self.base / "other"
        git(self.base, "init", "--bare", str(self.remote))
        git(self.base, "clone", str(self.remote), str(self.local))
        configure(self.local)
        (self.local / "README.md").write_text("base\n", encoding="utf-8")
        git(self.local, "add", "README.md")
        git(self.local, "commit", "-m", "base")
        git(self.local, "branch", "-M", "main")
        git(self.local, "push", "-u", "origin", "main")
        git(self.base, "clone", str(self.remote), str(self.other))
        configure(self.other)
        git(self.other, "switch", "main")
        self.service = GitService(str(self.local))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_remote_branch_browser_and_tracking_branch(self) -> None:
        git(self.other, "switch", "-c", "feature/remote")
        (self.other / "remote.txt").write_text("remote branch\n", encoding="utf-8")
        git(self.other, "add", "remote.txt")
        git(self.other, "commit", "-m", "remote branch work")
        git(self.other, "push", "-u", "origin", "feature/remote")
        self.service.fetch()
        names = [entry.name for entry in self.service.remote_branches()]
        self.assertIn("origin/feature/remote", names)
        self.service.create_tracking_branch("origin/feature/remote", "feature/local-track")
        self.assertEqual(self.service.branch(), "feature/local-track")
        self.assertEqual(self.service.upstream(), "origin/feature/remote")

    def test_annotated_tag_create_push_and_local_delete(self) -> None:
        self.service.create_annotated_tag("v-test", "RepoFlow test tag")
        self.assertIn("v-test", [tag.name for tag in self.service.tags()])
        self.service.push_tag("v-test")
        remote_tags = git(self.base, "--git-dir", str(self.remote), "tag", "--list").stdout.splitlines()
        self.assertIn("v-test", remote_tags)
        self.service.delete_tag("v-test")
        self.assertNotIn("v-test", [tag.name for tag in self.service.tags()])
        # Local delete must not delete the already-pushed remote tag.
        remote_tags = git(self.base, "--git-dir", str(self.remote), "tag", "--list").stdout.splitlines()
        self.assertIn("v-test", remote_tags)

    def test_sync_commit_lists_separate_local_and_upstream_only(self) -> None:
        (self.local / "local.txt").write_text("local\n", encoding="utf-8")
        git(self.local, "add", "local.txt")
        git(self.local, "commit", "-m", "local only")
        (self.other / "remote.txt").write_text("remote\n", encoding="utf-8")
        git(self.other, "add", "remote.txt")
        git(self.other, "commit", "-m", "remote only")
        git(self.other, "push")
        self.service.fetch()
        local_only, remote_only = self.service.sync_commit_lists()
        self.assertEqual([c.subject for c in local_only], ["local only"])
        self.assertEqual([c.subject for c in remote_only], ["remote only"])


if __name__ == "__main__":
    unittest.main()

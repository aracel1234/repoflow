from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class FirstPushUpstreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-upstream-")
        base = Path(self.tmp.name)
        self.remote = base / "remote.git"
        self.local = base / "local"
        self.local.mkdir()
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.local, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "RepoFlow Test"], cwd=self.local, check=True)
        subprocess.run(["git", "config", "user.email", "repoflow-test@example.invalid"], cwd=self.local, check=True)
        (self.local / "README.md").write_text("RepoFlow upstream test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.local, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.local, check=True, capture_output=True, text=True)
        self.git = GitService(str(self.local))
        self.git.add_remote(str(self.remote), "origin")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_first_push_sets_origin_main_upstream(self) -> None:
        self.assertIsNone(self.git.upstream())
        self.git.push()
        self.assertEqual(self.git.upstream(), "origin/main")
        info = self.git.repo_info()
        self.assertEqual(info.ahead, 0)
        self.assertEqual(info.behind, 0)


if __name__ == "__main__":
    unittest.main()

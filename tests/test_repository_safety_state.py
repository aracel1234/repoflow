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


class RepositorySafetyStateTests(unittest.TestCase):
    def test_conflicted_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repoflow-conflict-") as tmp:
            root = Path(tmp)
            git(root, "init", "-b", "main")
            configure(root)
            target = root / "shared.txt"
            target.write_text("base\n", encoding="utf-8")
            git(root, "add", "shared.txt")
            git(root, "commit", "-m", "base")
            git(root, "switch", "-c", "feature")
            target.write_text("feature\n", encoding="utf-8")
            git(root, "commit", "-am", "feature")
            git(root, "switch", "main")
            target.write_text("main\n", encoding="utf-8")
            git(root, "commit", "-am", "main")
            merge = git(root, "merge", "feature", check=False)
            self.assertNotEqual(merge.returncode, 0)
            service = GitService(str(root))
            conflicts = service.conflicted_files()
            self.assertEqual([entry.path for entry in conflicts], ["shared.txt"])

    def test_ahead_and_behind_identify_divergence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repoflow-diverge-") as tmp:
            base = Path(tmp)
            remote = base / "remote.git"
            local = base / "local"
            other = base / "other"
            git(base, "init", "--bare", str(remote))
            git(base, "clone", str(remote), str(local))
            configure(local)
            (local / "README.md").write_text("base\n", encoding="utf-8")
            git(local, "add", "README.md")
            git(local, "commit", "-m", "base")
            git(local, "branch", "-M", "main")
            git(local, "push", "-u", "origin", "main")

            git(base, "clone", str(remote), str(other))
            configure(other)
            git(other, "switch", "main")
            (other / "remote.txt").write_text("remote\n", encoding="utf-8")
            git(other, "add", "remote.txt")
            git(other, "commit", "-m", "remote")
            git(other, "push")

            (local / "local.txt").write_text("local\n", encoding="utf-8")
            git(local, "add", "local.txt")
            git(local, "commit", "-m", "local")
            service = GitService(str(local))
            service.fetch()
            info = service.repo_info()
            self.assertEqual((info.ahead, info.behind), (1, 1))


if __name__ == "__main__":
    unittest.main()

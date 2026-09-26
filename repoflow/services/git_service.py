from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from repoflow.core.models import CommitInfo, GitFile, RepoInfo


class GitError(RuntimeError):
    def __init__(self, message: str, command: list[str] | None = None, stderr: str = ""):
        super().__init__(message)
        self.command = command or []
        self.stderr = stderr


@dataclass(slots=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class GitService:
    def __init__(self, repo_path: str | None = None):
        self.repo_path = str(Path(repo_path).expanduser().resolve()) if repo_path else None

    @staticmethod
    def git_available() -> bool:
        try:
            subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def _askpass_path() -> Path:
        path = Path.home() / ".cache" / "repoflow" / "git-askpass.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        script = """#!/usr/bin/env sh
case "$1" in
  *sername*) printf '%s\\n' "${REPOFLOW_GITHUB_USER:-x-access-token}" ;;
  *) printf '%s\\n' "${REPOFLOW_GITHUB_TOKEN:-}" ;;
esac
"""
        if not path.exists() or path.read_text(encoding="utf-8", errors="ignore") != script:
            path.write_text(script, encoding="utf-8")
            path.chmod(0o700)
        return path

    @staticmethod
    def is_github_url(url: str | None) -> bool:
        if not url:
            return False
        value = url.strip().lower()
        if value.startswith("git@github.com:"):
            return True
        if value.startswith("ssh://git@github.com/"):
            return True
        try:
            parsed = urlparse(value)
            return parsed.hostname == "github.com"
        except ValueError:
            return False

    @classmethod
    def _auth_env(cls, token: str | None, username: str | None, remote_url: str | None) -> dict[str, str]:
        if not token or not cls.is_github_url(remote_url):
            return {}
        return {
            "GIT_ASKPASS": str(cls._askpass_path()),
            "GIT_ASKPASS_REQUIRE": "force",
            "REPOFLOW_GITHUB_TOKEN": token,
            "REPOFLOW_GITHUB_USER": username or "x-access-token",
        }

    def _run(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        check: bool = True,
        input_text: str | None = None,
        env_extra: dict[str, str] | None = None,
    ) -> CommandResult:
        command = ["git", *args]
        workdir = cwd or self.repo_path
        if not workdir:
            raise GitError("Repository path is not set.", command)
        env = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
        if env_extra:
            env.update(env_extra)
        try:
            proc = subprocess.run(
                command,
                cwd=workdir,
                input=input_text,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise GitError("Git is not installed or not available in PATH.", command) from exc
        if check and proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise GitError(detail or "Git command failed.", command, proc.stderr)
        return CommandResult(proc.stdout, proc.stderr, proc.returncode)

    @staticmethod
    def is_repository(path: str) -> bool:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path,
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"},
            )
            return proc.returncode == 0 and proc.stdout.strip() == "true"
        except (FileNotFoundError, OSError):
            return False

    @staticmethod
    def init_repository(path: str, initial_branch: str = "main") -> str:
        Path(path).mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["git", "init", "-b", initial_branch],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        if proc.returncode != 0:
            raise GitError((proc.stderr or proc.stdout).strip() or "Could not initialize repository.")
        return str(Path(path).resolve())

    @classmethod
    def clone_repository(
        cls,
        url: str,
        destination: str,
        *,
        token: str | None = None,
        username: str | None = None,
    ) -> str:
        parent = str(Path(destination).expanduser().resolve().parent)
        target = str(Path(destination).expanduser().resolve())
        Path(parent).mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
        env.update(cls._auth_env(token, username, url))
        proc = subprocess.run(
            ["git", "clone", url, target],
            cwd=parent,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            raise GitError((proc.stderr or proc.stdout).strip() or "Clone failed.")
        return target

    def root(self) -> str:
        return self._run(["rev-parse", "--show-toplevel"]).stdout.strip()

    def branch(self) -> str:
        branch = self._run(["branch", "--show-current"]).stdout.strip()
        if branch:
            return branch
        short = self._run(["rev-parse", "--short", "HEAD"], check=False).stdout.strip()
        return f"detached@{short}" if short else "(no commits)"

    def remote_names(self) -> list[str]:
        out = self._run(["remote"], check=False).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]

    def remote_url(self, remote: str = "origin") -> str | None:
        result = self._run(["remote", "get-url", remote], check=False)
        return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    def upstream(self) -> str | None:
        result = self._run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], check=False)
        return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    def ahead_behind(self) -> tuple[int, int]:
        if not self.upstream():
            return (0, 0)
        result = self._run(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], check=False)
        if result.returncode != 0:
            return (0, 0)
        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return (0, 0)
        return int(parts[0]), int(parts[1])

    def repo_info(self) -> RepoInfo:
        root = self.root()
        names = self.remote_names()
        remote_name = "origin" if "origin" in names else (names[0] if names else None)
        upstream = self.upstream()
        ahead, behind = self.ahead_behind()
        return RepoInfo(
            root=root,
            name=Path(root).name,
            branch=self.branch(),
            remote_name=remote_name,
            remote_url=self.remote_url(remote_name) if remote_name else None,
            upstream=upstream,
            ahead=ahead,
            behind=behind,
        )

    def status(self) -> list[GitFile]:
        raw = self._run(["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout
        if not raw:
            return []
        records = raw.split("\0")
        result: list[GitFile] = []
        i = 0
        while i < len(records):
            record = records[i]
            if not record:
                i += 1
                continue
            if len(record) < 3:
                i += 1
                continue
            x, y = record[0], record[1]
            path = record[3:]
            original = None
            if x in {"R", "C"} or y in {"R", "C"}:
                if i + 1 < len(records) and records[i + 1]:
                    original = path
                    path = records[i + 1]
                    i += 1
            result.append(GitFile(path=path, index_status=x, worktree_status=y, original_path=original))
            i += 1
        return result

    def stage(self, paths: Iterable[str]) -> None:
        items = list(paths)
        if items:
            self._run(["add", "--", *items])

    def unstage(self, paths: Iterable[str]) -> None:
        items = list(paths)
        if not items:
            return
        has_head = self._run(["rev-parse", "--verify", "HEAD"], check=False).returncode == 0
        if has_head:
            self._run(["restore", "--staged", "--", *items])
        else:
            self._run(["rm", "--cached", "-r", "--ignore-unmatch", "--", *items], check=False)

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    @staticmethod
    def _looks_binary(data: bytes) -> bool:
        if not data:
            return False
        if b"\x00" in data:
            return True
        sample = data[:8192]
        try:
            text = sample.decode("utf-8")
        except UnicodeDecodeError:
            return True
        if not text:
            return False
        control = sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t\f\b")
        return (control / max(len(text), 1)) > 0.05

    def _binary_preview(self, path: str, *, staged: bool) -> str:
        absolute = Path(self.root()) / path
        size_line = ""
        try:
            if absolute.is_file():
                size_line = f"\nSize: {self._format_size(absolute.stat().st_size)}"
        except OSError:
            pass
        state = "staged" if staged else "working-tree"
        return (
            "Binary file\n"
            "Preview is not available for binary files.\n\n"
            f"File: {path}\n"
            f"State: {state}{size_line}"
        )

    def diff(self, path: str, *, staged: bool = False) -> str:
        args = ["diff", "--no-ext-diff", "--no-color"]
        if staged:
            args.append("--cached")
        args.extend(["--", path])
        result = self._run(args, check=False)
        text = result.stdout
        if "Binary files " in text and " differ" in text:
            return self._binary_preview(path, staged=staged)
        if not text and not staged:
            absolute = Path(self.root()) / path
            if absolute.is_file():
                try:
                    raw = absolute.read_bytes()
                    if self._looks_binary(raw):
                        return self._binary_preview(path, staged=False)
                    data = raw.decode("utf-8")
                    lines = data.splitlines()
                    preview = "\n".join(f"+ {line}" for line in lines[:500])
                    if len(lines) > 500:
                        preview += "\n… preview truncated …"
                    return preview
                except (OSError, UnicodeDecodeError):
                    return self._binary_preview(path, staged=False)
        return text or "No textual diff available."

    def staged_diff(self, path: str) -> str:
        return self.diff(path, staged=True)

    def commit(self, message: str) -> str:
        message = message.strip()
        if not message:
            raise GitError("Commit message cannot be empty.")
        return self._run(["commit", "-m", message]).stdout.strip()

    def add_remote(self, url: str, name: str = "origin") -> None:
        if name in self.remote_names():
            self._run(["remote", "set-url", name, url])
        else:
            self._run(["remote", "add", name, url])

    def remove_remote(self, name: str = "origin") -> None:
        self._run(["remote", "remove", name])

    def fetch(self, remote: str | None = None, *, token: str | None = None, username: str | None = None) -> str:
        info = self.repo_info()
        target_remote = remote or info.remote_name
        url = self.remote_url(target_remote) if target_remote else None
        args = ["fetch", "--prune"]
        if remote:
            args.append(remote)
        result = self._run(args, env_extra=self._auth_env(token, username, url))
        return result.stderr.strip() or "Fetch completed."

    def push(self, *, token: str | None = None, username: str | None = None) -> str:
        info = self.repo_info()
        if not info.remote_name:
            raise GitError("This repository does not have a remote yet.")
        if info.branch.startswith("detached@") or info.branch == "(no commits)":
            raise GitError("Push requires an active branch with at least one commit.")
        env = self._auth_env(token, username, info.remote_url)
        if info.upstream:
            result = self._run(["push"], env_extra=env)
        else:
            result = self._run(["push", "-u", info.remote_name, info.branch], env_extra=env)
        return (result.stderr or result.stdout).strip() or "Push completed."

    def pull_ff_only(self, *, token: str | None = None, username: str | None = None) -> str:
        info = self.repo_info()
        if not info.upstream:
            raise GitError("No upstream branch is configured. Push once to establish it, or configure an upstream.")
        if info.ahead > 0 and info.behind > 0:
            raise GitError(
                f"Local and remote histories have diverged (ahead {info.ahead}, behind {info.behind}). "
                "RepoFlow will not merge or rebase automatically."
            )
        if info.behind == 0:
            return "Already up to date."
        env = self._auth_env(token, username, info.remote_url)
        result = self._run(["pull", "--ff-only"], env_extra=env)
        return (result.stdout or result.stderr).strip() or "Pull completed."

    def history(self, limit: int = 100) -> list[CommitInfo]:
        fmt = "%H%x1f%h%x1f%s%x1f%an%x1f%ar%x1e"
        result = self._run(["log", f"--max-count={limit}", f"--pretty=format:{fmt}"], check=False)
        if result.returncode != 0:
            return []
        commits: list[CommitInfo] = []
        for record in result.stdout.split("\x1e"):
            record = record.strip("\n")
            if not record:
                continue
            parts = record.split("\x1f")
            if len(parts) == 5:
                commits.append(CommitInfo(*parts))
        return commits

    def local_branches(self) -> list[str]:
        out = self._run(["for-each-ref", "--format=%(refname:short)", "refs/heads/"]).stdout
        return [x.strip() for x in out.splitlines() if x.strip()]

    def validate_branch_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise GitError("Branch name cannot be empty.")
        result = self._run(["check-ref-format", "--branch", name], check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise GitError(detail or f"Invalid branch name: {name}")
        return name

    def create_branch(self, name: str, *, switch: bool = True) -> None:
        name = self.validate_branch_name(name)
        if name in self.local_branches():
            raise GitError(f"Branch '{name}' already exists.")

        if switch:
            self._run(["switch", "-c", name])
            active = self.branch()
            if active != name:
                raise GitError(
                    f"Git created the branch but RepoFlow could not switch to it. Active branch: {active}"
                )
        else:
            self._run(["branch", name])

    def switch_branch(self, name: str) -> None:
        name = self.validate_branch_name(name)
        if name not in self.local_branches():
            raise GitError(f"Local branch '{name}' does not exist.")
        self._run(["switch", name])
        active = self.branch()
        if active != name:
            raise GitError(f"Could not switch to branch '{name}'. Active branch: {active}")

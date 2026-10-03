from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FileKind(str, Enum):
    MODIFIED = "Modified"
    ADDED = "Added"
    DELETED = "Deleted"
    RENAMED = "Renamed"
    COPIED = "Copied"
    UNTRACKED = "New"
    CONFLICT = "Conflict"
    UNKNOWN = "Changed"


@dataclass(slots=True)
class GitFile:
    path: str
    index_status: str
    worktree_status: str
    original_path: str | None = None

    @property
    def staged(self) -> bool:
        return self.index_status not in {" ", "?", "!"}

    @property
    def unstaged(self) -> bool:
        return self.worktree_status not in {" ", "?", "!"}

    @property
    def untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"

    @property
    def partially_staged(self) -> bool:
        """True when the file has both index and working-tree changes."""
        return self.staged and self.unstaged and not self.conflicted

    @property
    def fully_staged(self) -> bool:
        """True when all currently detected changes are staged."""
        return self.staged and not self.unstaged and not self.conflicted

    @property
    def stage_label(self) -> str:
        if self.conflicted:
            return "Conflict"
        if self.partially_staged:
            return "Partially staged"
        if self.fully_staged:
            return "Staged"
        return "Unstaged"

    @property
    def conflicted(self) -> bool:
        return (self.index_status + self.worktree_status) in {
            "DD", "AU", "UD", "UA", "DU", "AA", "UU"
        }

    @property
    def kind(self) -> FileKind:
        if self.conflicted:
            return FileKind.CONFLICT
        if self.untracked:
            return FileKind.UNTRACKED
        code = self.worktree_status if self.worktree_status not in {" ", "?"} else self.index_status
        return {
            "M": FileKind.MODIFIED,
            "A": FileKind.ADDED,
            "D": FileKind.DELETED,
            "R": FileKind.RENAMED,
            "C": FileKind.COPIED,
        }.get(code, FileKind.UNKNOWN)


@dataclass(slots=True)
class RepoInfo:
    root: str
    name: str
    branch: str
    remote_name: str | None
    remote_url: str | None
    upstream: str | None
    ahead: int = 0
    behind: int = 0


@dataclass(slots=True)
class CommitInfo:
    sha: str
    short_sha: str
    subject: str
    author: str
    relative_date: str


@dataclass(slots=True)
class StashInfo:
    ref: str
    subject: str
    relative_date: str


@dataclass(slots=True)
class CommitDetail:
    sha: str
    short_sha: str
    subject: str
    body: str
    author: str
    author_email: str
    authored_at: str
    parent_count: int
    files: list[str]
    patch: str


@dataclass(slots=True)
class RemoteBranchInfo:
    name: str
    short_sha: str
    subject: str


@dataclass(slots=True)
class TagInfo:
    name: str
    short_sha: str
    relative_date: str
    subject: str


@dataclass(slots=True)
class DiffHunk:
    header: str
    body: str

    @property
    def preview(self) -> str:
        return f"{self.header}\n{self.body}".strip()


@dataclass(slots=True)
class GitHubUser:
    login: str
    name: str | None
    html_url: str
    avatar_url: str
    public_repos: int = 0


@dataclass(slots=True)
class GitHubRepository:
    name: str
    full_name: str
    owner: str
    private: bool
    description: str | None
    html_url: str
    clone_url: str
    ssh_url: str
    default_branch: str
    updated_at: str

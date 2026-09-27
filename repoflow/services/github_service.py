from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from repoflow.core.models import GitHubRepository, GitHubUser


class GitHubError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GitHubService:
    API_BASE = "https://api.github.com"
    API_VERSION = "2026-03-10"
    USER_AGENT = "RepoFlow/0.3.0"

    def __init__(self, token: str):
        token = token.strip()
        if not token:
            raise GitHubError("GitHub token is missing.")
        self.token = token

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, str | int] | None = None,
    ) -> Any:
        url = self.API_BASE + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": self.API_VERSION,
                "User-Agent": self.USER_AGENT,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            message = f"GitHub API request failed ({exc.code})."
            try:
                body = json.loads(exc.read().decode("utf-8", errors="replace"))
                api_message = body.get("message")
                errors = body.get("errors")
                if api_message:
                    message = str(api_message)
                if errors:
                    details = []
                    for item in errors:
                        if isinstance(item, dict):
                            details.append(str(item.get("message") or item.get("code") or item))
                        else:
                            details.append(str(item))
                    if details:
                        message += " — " + "; ".join(details)
            except Exception:
                pass
            if exc.code == 401:
                message = "GitHub rejected this token. Check that it is valid and has not expired."
            elif exc.code == 403:
                message += " Check the token permissions and repository access."
            elif exc.code == 404:
                message += " The resource may be unavailable to this token."
            raise GitHubError(message, exc.code) from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"Could not reach GitHub: {exc.reason}") from exc
        except TimeoutError as exc:
            raise GitHubError("GitHub request timed out.") from exc

    def get_user(self) -> GitHubUser:
        data = self._request("GET", "/user")
        return GitHubUser(
            login=str(data.get("login", "")),
            name=data.get("name"),
            html_url=str(data.get("html_url", "")),
            avatar_url=str(data.get("avatar_url", "")),
            public_repos=int(data.get("public_repos", 0) or 0),
        )

    def list_repositories(self) -> list[GitHubRepository]:
        repos: list[GitHubRepository] = []
        page = 1
        while page <= 10:
            data = self._request(
                "GET",
                "/user/repos",
                query={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if not isinstance(data, list):
                break
            for item in data:
                repos.append(self._repo_from_json(item))
            if len(data) < 100:
                break
            page += 1
        return repos

    def create_repository(self, name: str, description: str = "", private: bool = False) -> GitHubRepository:
        name = name.strip()
        if not name:
            raise GitHubError("Repository name cannot be empty.")
        data = self._request(
            "POST",
            "/user/repos",
            payload={
                "name": name,
                "description": description.strip(),
                "private": bool(private),
                # Keep the remote history empty so an existing local project can
                # be connected and pushed without unrelated-history conflicts.
                "auto_init": False,
            },
        )
        return self._repo_from_json(data)

    @staticmethod
    def _repo_from_json(item: dict[str, Any]) -> GitHubRepository:
        owner = item.get("owner") or {}
        return GitHubRepository(
            name=str(item.get("name", "")),
            full_name=str(item.get("full_name", "")),
            owner=str(owner.get("login", "")),
            private=bool(item.get("private", False)),
            description=item.get("description"),
            html_url=str(item.get("html_url", "")),
            clone_url=str(item.get("clone_url", "")),
            ssh_url=str(item.get("ssh_url", "")),
            default_branch=str(item.get("default_branch", "main") or "main"),
            updated_at=str(item.get("updated_at", "")),
        )

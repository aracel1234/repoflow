from __future__ import annotations

import json
from pathlib import Path


class AppSettings:
    def __init__(self) -> None:
        self.dir = Path.home() / ".config" / "repoflow"
        self.path = self.dir / "settings.json"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data = {
            "repositories": [],
            "last_repository": None,
            "github_login": None,
            "github_name": None,
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    @property
    def repositories(self) -> list[str]:
        return [str(x) for x in self.data.get("repositories", [])]

    @property
    def github_login(self) -> str | None:
        value = self.data.get("github_login")
        return str(value) if value else None

    def add_repository(self, path: str) -> None:
        path = str(Path(path).resolve())
        repos = [x for x in self.repositories if x != path]
        repos.insert(0, path)
        self.data["repositories"] = repos[:30]
        self.data["last_repository"] = path
        self.save()

    def remove_repository(self, path: str) -> None:
        self.data["repositories"] = [x for x in self.repositories if x != path]
        if self.data.get("last_repository") == path:
            self.data["last_repository"] = None
        self.save()

    def set_github_identity(self, login: str | None, name: str | None = None) -> None:
        self.data["github_login"] = login
        self.data["github_name"] = name
        self.save()

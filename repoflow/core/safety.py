from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re


@dataclass(frozen=True, slots=True)
class SafetyIssue:
    path: str
    category: str
    severity: str
    title: str
    detail: str
    size_bytes: int | None = None


class SafetyScanner:
    """Conservative pre-commit checks for files that deserve user review.

    RepoFlow never silently blocks a local Git operation based only on a filename.
    The scanner exists to surface likely secrets and unusually large files before
    they are staged/committed so the user can make an informed choice.
    """

    LARGE_FILE_WARNING_BYTES = 25 * 1024 * 1024
    VERY_LARGE_FILE_BYTES = 100 * 1024 * 1024

    _SAFE_ENV_EXAMPLES = {
        ".env.example",
        ".env.sample",
        ".env.template",
        ".env.defaults",
    }
    _SENSITIVE_EXACT_NAMES = {
        ".netrc",
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "key.properties",
        "keystore.properties",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
    _SENSITIVE_SUFFIXES = {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
        ".jks",
        ".keystore",
        ".tfstate",
    }
    _SERVICE_ACCOUNT_RE = re.compile(r"service[-_]?account.*\.(?:json|ya?ml)$", re.IGNORECASE)

    @staticmethod
    def normalize_path(path: str) -> str:
        value = path.replace("\\", "/")
        while value.startswith("./"):
            value = value[2:]
        value = value.lstrip("/")
        return str(PurePosixPath(value))

    @classmethod
    def sensitive_reason(cls, path: str) -> str | None:
        normalized = cls.normalize_path(path)
        lower = normalized.lower()
        name = PurePosixPath(lower).name

        if name in cls._SAFE_ENV_EXAMPLES:
            return None
        if name == ".env" or (name.startswith(".env.") and name not in cls._SAFE_ENV_EXAMPLES):
            return "Environment files often contain API keys, passwords, or connection strings."
        if name in cls._SENSITIVE_EXACT_NAMES:
            return "This filename commonly contains credentials, tokens, or private key material."
        if any(name.endswith(suffix) for suffix in cls._SENSITIVE_SUFFIXES):
            return "This file type commonly contains private keys, signing credentials, or sensitive state."
        if name.endswith(".tfstate.backup"):
            return "Terraform state can contain credentials and other sensitive infrastructure values."
        if cls._SERVICE_ACCOUNT_RE.search(name):
            return "Service-account files commonly contain private credentials."
        if lower.endswith("/.aws/credentials") or lower == ".aws/credentials":
            return "AWS credentials files contain access credentials."
        if lower.endswith("application_default_credentials.json"):
            return "Application default credentials contain authentication material."
        return None

    @classmethod
    def inspect_path(cls, repo_root: str, path: str) -> list[SafetyIssue]:
        normalized = cls.normalize_path(path)
        issues: list[SafetyIssue] = []

        reason = cls.sensitive_reason(normalized)
        if reason:
            issues.append(
                SafetyIssue(
                    path=normalized,
                    category="sensitive",
                    severity="high",
                    title="Potentially sensitive file",
                    detail=reason,
                )
            )

        candidate = Path(repo_root) / normalized
        try:
            size = candidate.stat().st_size if candidate.is_file() else None
        except OSError:
            size = None

        if size is not None and size >= cls.LARGE_FILE_WARNING_BYTES:
            if size >= cls.VERY_LARGE_FILE_BYTES:
                severity = "high"
                detail = (
                    "This file is very large for a normal Git commit. Many hosted Git services impose "
                    "strict per-file limits; consider Git LFS or another artifact store."
                )
            else:
                severity = "medium"
                detail = (
                    "Large binary/data files can make repository history permanently heavy. "
                    "Consider Git LFS or excluding generated artifacts if appropriate."
                )
            issues.append(
                SafetyIssue(
                    path=normalized,
                    category="large_file",
                    severity=severity,
                    title="Large file",
                    detail=detail,
                    size_bytes=size,
                )
            )
        return issues

    @classmethod
    def inspect_paths(cls, repo_root: str, paths: list[str]) -> list[SafetyIssue]:
        issues: list[SafetyIssue] = []
        for path in paths:
            issues.extend(cls.inspect_path(repo_root, path))
        return issues

    @staticmethod
    def format_size(size: int | None) -> str:
        if size is None:
            return ""
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    @classmethod
    def exact_gitignore_pattern(cls, path: str) -> str:
        """Return a repository-root anchored literal-ish gitignore pattern."""
        normalized = cls.normalize_path(path)
        escaped = []
        for char in normalized:
            if char in {"\\", "*", "?", "[", "]", "!", "#", " "}:
                escaped.append("\\" + char)
            else:
                escaped.append(char)
        return "/" + "".join(escaped)

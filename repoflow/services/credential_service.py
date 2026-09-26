from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(slots=True)
class CredentialSaveResult:
    persisted: bool
    message: str


class CredentialService:
    """GitHub token storage with zero Python crypto/keyring dependencies.

    The token always exists in memory for the current RepoFlow session.
    When `secret-tool` is available, RepoFlow also attempts to persist it
    using the desktop Secret Service. If the service/tool is unavailable,
    persistence safely falls back to session-only storage.
    """

    LABEL = "RepoFlow GitHub token"
    ATTRS = ("application", "repoflow", "service", "github", "account", "token")

    def __init__(self) -> None:
        self._session_token: str | None = None

    @staticmethod
    def _secret_tool() -> str | None:
        return shutil.which("secret-tool")

    @classmethod
    def secure_storage_available(cls) -> bool:
        return cls._secret_tool() is not None

    @classmethod
    def _run_secret_tool(
        cls,
        args: list[str],
        *,
        input_text: str | None = None,
        timeout: float = 15.0,
    ) -> subprocess.CompletedProcess[str] | None:
        tool = cls._secret_tool()
        if tool is None:
            return None
        try:
            return subprocess.run(
                [tool, *args],
                input=input_text,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    def get_token(self) -> str | None:
        if self._session_token:
            return self._session_token

        result = self._run_secret_tool(["lookup", *self.ATTRS])
        if result is None or result.returncode != 0:
            return None

        token = result.stdout.strip()
        if token:
            self._session_token = token
            return token
        return None

    def set_token(self, token: str, *, remember: bool) -> CredentialSaveResult:
        token = token.strip()
        if not token:
            raise ValueError("GitHub token cannot be empty.")

        # Always keep it in RAM so GitHub operations work immediately.
        self._session_token = token

        if not remember:
            return CredentialSaveResult(
                False,
                "Token will be kept only until RepoFlow closes.",
            )

        if not self.secure_storage_available():
            return CredentialSaveResult(
                False,
                "Secure system credential storage is unavailable; token is session-only.",
            )

        result = self._run_secret_tool(
            ["store", f"--label={self.LABEL}", *self.ATTRS],
            input_text=token,
        )
        if result is not None and result.returncode == 0:
            return CredentialSaveResult(
                True,
                "Token saved using the system Secret Service.",
            )

        return CredentialSaveResult(
            False,
            "Secure credential storage could not save the token; token is session-only.",
        )

    def clear(self) -> None:
        self._session_token = None
        self._run_secret_tool(["clear", *self.ATTRS])

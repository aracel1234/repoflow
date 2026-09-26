from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(slots=True)
class CredentialSaveResult:
    persisted: bool
    message: str


@dataclass(slots=True)
class SecureStorageStatus:
    available: bool
    backend: str
    message: str


class CredentialService:
    """GitHub token storage with no Python keyring/crypto dependency.

    The token always exists in memory for the current RepoFlow session.
    Persistent storage uses the freedesktop Secret Service through
    ``secret-tool`` when that helper is installed and the desktop secret
    service accepts the write.
    """

    LABEL = "RepoFlow GitHub token"
    ATTRS = ("application", "repoflow", "service", "github", "account", "token")

    def __init__(self) -> None:
        self._session_token: str | None = None

    @staticmethod
    def _secret_tool() -> str | None:
        return shutil.which("secret-tool")

    @classmethod
    def secure_storage_status(cls) -> SecureStorageStatus:
        tool = cls._secret_tool()
        if tool is None:
            return SecureStorageStatus(
                False,
                "missing-secret-tool",
                "Secure storage helper 'secret-tool' is not installed. "
                "On KDE Neon/Ubuntu install it with: sudo apt install libsecret-tools",
            )
        return SecureStorageStatus(
            True,
            "secret-service",
            f"Secret Service helper available at {tool}.",
        )

    @classmethod
    def secure_storage_available(cls) -> bool:
        return cls.secure_storage_status().available

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

        self._session_token = token

        if not remember:
            return CredentialSaveResult(
                False,
                "Token will be kept only until RepoFlow closes.",
            )

        status = self.secure_storage_status()
        if not status.available:
            return CredentialSaveResult(False, status.message + " Token is session-only for now.")

        result = self._run_secret_tool(
            ["store", f"--label={self.LABEL}", *self.ATTRS],
            input_text=token,
        )
        if result is not None and result.returncode == 0:
            return CredentialSaveResult(
                True,
                "Token saved securely using the system Secret Service.",
            )

        detail = ""
        if result is not None:
            detail = (result.stderr or result.stdout or "").strip()
        suffix = f" Details: {detail}" if detail else ""
        return CredentialSaveResult(
            False,
            "'secret-tool' is installed, but the desktop Secret Service could not save the token. "
            "Ensure a Secret Service provider is available/unlocked in your desktop session."
            + suffix
            + " Token is session-only for now.",
        )

    def clear(self) -> None:
        self._session_token = None
        self._run_secret_tool(["clear", *self.ATTRS])

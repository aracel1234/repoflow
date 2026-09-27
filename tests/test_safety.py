from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repoflow.core.safety import SafetyScanner


class SafetyScannerTests(unittest.TestCase):
    def test_sensitive_names_are_flagged(self) -> None:
        flagged = [
            ".env",
            ".env.production",
            "credentials.json",
            "config/service-account-prod.json",
            "keys/id_ed25519",
            "release/app-signing.jks",
            "terraform/prod.tfstate",
        ]
        for path in flagged:
            with self.subTest(path=path):
                self.assertIsNotNone(SafetyScanner.sensitive_reason(path))

    def test_safe_env_examples_are_not_flagged(self) -> None:
        for path in (".env.example", ".env.sample", ".env.template"):
            with self.subTest(path=path):
                self.assertIsNone(SafetyScanner.sensitive_reason(path))

    def test_large_file_is_flagged_without_reading_contents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repoflow-safety-") as tmp:
            path = Path(tmp) / "artifact.bin"
            path.write_bytes(b"")
            with path.open("r+b") as handle:
                handle.truncate(SafetyScanner.LARGE_FILE_WARNING_BYTES + 1)
            issues = SafetyScanner.inspect_path(tmp, "artifact.bin")
            self.assertTrue(any(issue.category == "large_file" for issue in issues))

    def test_exact_gitignore_pattern_preserves_dotfiles_and_escapes_spaces(self) -> None:
        self.assertEqual(SafetyScanner.exact_gitignore_pattern(".env"), "/.env")
        self.assertEqual(
            SafetyScanner.exact_gitignore_pattern("keys/private file.key"),
            "/keys/private\\ file.key",
        )


if __name__ == "__main__":
    unittest.main()

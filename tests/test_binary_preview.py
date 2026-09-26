from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from repoflow.services.git_service import GitService


class BinaryPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="repoflow-binary-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True, text=True)
        self.git = GitService(str(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_untracked_binary_is_not_decoded_as_text(self) -> None:
        image = self.root / "avatar-pixel.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + bytes(range(1, 80)))
        preview = self.git.diff("avatar-pixel.png")
        self.assertIn("Binary file", preview)
        self.assertIn("Preview is not available", preview)
        self.assertNotIn("�PNG", preview)

    def test_staged_binary_uses_friendly_preview(self) -> None:
        image = self.root / "avatar-pixel.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + bytes(range(1, 80)))
        self.git.stage(["avatar-pixel.png"])
        preview = self.git.staged_diff("avatar-pixel.png")
        self.assertIn("Binary file", preview)
        self.assertNotIn("Binary files /dev/null", preview)


if __name__ == "__main__":
    unittest.main()

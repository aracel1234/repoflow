from __future__ import annotations

import unittest

from repoflow.core.models import GitFile


class GitFileStateTests(unittest.TestCase):
    def test_partial_state(self) -> None:
        item = GitFile("README.md", "M", "M")
        self.assertTrue(item.staged)
        self.assertTrue(item.unstaged)
        self.assertTrue(item.partially_staged)
        self.assertFalse(item.fully_staged)
        self.assertEqual(item.stage_label, "Partially staged")

    def test_fully_staged_state(self) -> None:
        item = GitFile("README.md", "M", " ")
        self.assertTrue(item.fully_staged)
        self.assertFalse(item.partially_staged)
        self.assertEqual(item.stage_label, "Staged")

    def test_unstaged_state(self) -> None:
        item = GitFile("README.md", " ", "M")
        self.assertFalse(item.staged)
        self.assertTrue(item.unstaged)
        self.assertEqual(item.stage_label, "Unstaged")


if __name__ == "__main__":
    unittest.main()

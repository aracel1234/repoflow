from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "repoflow" / "services" / "git_service.py").read_text(encoding="utf-8")
DIALOGS = (ROOT / "repoflow" / "ui" / "dialogs.py").read_text(encoding="utf-8")


class Stage3Batch2UIRegressionTests(unittest.TestCase):
    def test_hunk_staging_is_explicit_separate_action(self) -> None:
        self.assertIn('QPushButton("Stage Selected Hunks…")', MAIN)
        self.assertIn("def stage_selected_hunks", MAIN)
        self.assertIn("def stage_hunks", SERVICE)

    def test_stash_manager_is_exposed(self) -> None:
        self.assertIn('QAction("Stashes…", self)', MAIN)
        self.assertIn("class StashManagerDialog", DIALOGS)

    def test_branch_delete_is_never_forced(self) -> None:
        self.assertIn('["branch", "-d", name]', SERVICE)
        self.assertNotIn('["branch", "-D", name]', SERVICE)

    def test_conflict_review_does_not_auto_choose_ours_or_theirs(self) -> None:
        self.assertIn("class ConflictReviewDialog", DIALOGS)
        self.assertNotIn('checkout", "--ours', MAIN + SERVICE)
        self.assertNotIn('checkout", "--theirs', MAIN + SERVICE)


if __name__ == "__main__":
    unittest.main()

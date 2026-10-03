from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "repoflow" / "services" / "git_service.py").read_text(encoding="utf-8")
DIALOGS = (ROOT / "repoflow" / "ui" / "dialogs.py").read_text(encoding="utf-8")


class Stage3Batch3UIRegressionTests(unittest.TestCase):
    def test_history_detail_and_recovery_actions_are_exposed(self) -> None:
        self.assertIn('QPushButton("Copy Hash")', MAIN)
        self.assertIn('QPushButton("Open on GitHub")', MAIN)
        self.assertIn('QPushButton("Revert Commit…")', MAIN)
        self.assertIn('QPushButton("Cherry-pick Commit…")', MAIN)
        self.assertIn("def commit_detail", SERVICE)
        self.assertIn('QCheckBox("All local branches")', MAIN)
        self.assertIn("all_local_branches", SERVICE)

    def test_remote_branches_and_tags_are_explicit_tools(self) -> None:
        self.assertIn('QAction("Remote Branches…", self)', MAIN)
        self.assertIn('QAction("Tags…", self)', MAIN)
        self.assertIn("class RemoteBranchesDialog", DIALOGS)
        self.assertIn("class TagManagerDialog", DIALOGS)

    def test_tag_push_is_explicit_and_remote_delete_is_absent(self) -> None:
        self.assertIn('QPushButton("Push Selected Tag")', DIALOGS)
        self.assertIn('QPushButton("Delete Local Tag")', DIALOGS)
        self.assertNotIn('push", "--delete"', SERVICE)
        self.assertNotIn('tag", "-d", "origin', SERVICE)

    def test_recovery_avoids_history_rewriting_operations(self) -> None:
        combined = MAIN + SERVICE
        self.assertNotIn('reset", "--hard', combined)
        self.assertNotIn('push", "--force', combined)
        self.assertNotIn('push", "-f', combined)
        self.assertIn('["revert", "--no-edit", detail.sha]', SERVICE)
        self.assertIn('["cherry-pick", detail.sha]', SERVICE)

    def test_abort_current_operation_is_explicit(self) -> None:
        self.assertIn('QAction("Abort Current Git Operation…", self)', MAIN)
        self.assertIn('["cherry-pick", "--abort"]', SERVICE)
        self.assertIn('["merge", "--abort"]', SERVICE)
        self.assertIn('["revert", "--abort"]', SERVICE)


if __name__ == "__main__":
    unittest.main()

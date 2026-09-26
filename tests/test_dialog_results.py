from __future__ import annotations

from pathlib import Path
import re
import unittest


class DialogResultRegressionTests(unittest.TestCase):
    def test_main_window_never_uses_instance_accepted_enum(self):
        source = (Path(__file__).resolve().parents[1] / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\bdialog\.Accepted\b")

    def test_dialog_acceptance_uses_qdialog_dialogcode(self):
        source = (Path(__file__).resolve().parents[1] / "repoflow" / "ui" / "main_window.py").read_text(encoding="utf-8")
        checks = re.findall(r"dialog\.exec\(\) != ([^:\n]+)", source)
        self.assertTrue(checks)
        self.assertTrue(all("QDialog.DialogCode.Accepted" in check for check in checks))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from repoflow.services.credential_service import CredentialService


class CredentialServiceTests(unittest.TestCase):
    @patch("repoflow.services.credential_service.shutil.which", return_value=None)
    def test_missing_secret_tool_has_actionable_message(self, _which):
        service = CredentialService()
        result = service.set_token("test-token", remember=True)
        self.assertFalse(result.persisted)
        self.assertIn("libsecret-tools", result.message)
        self.assertEqual(service.get_token(), "test-token")

    @patch("repoflow.services.credential_service.shutil.which", return_value="/usr/bin/secret-tool")
    @patch("repoflow.services.credential_service.subprocess.run")
    def test_successful_secret_service_store_is_persisted(self, run, _which):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        result = CredentialService().set_token("test-token", remember=True)
        self.assertTrue(result.persisted)
        self.assertIn("saved securely", result.message.lower())

    @patch("repoflow.services.credential_service.shutil.which", return_value="/usr/bin/secret-tool")
    @patch("repoflow.services.credential_service.subprocess.run")
    def test_secret_service_failure_reports_backend_problem(self, run, _which):
        run.return_value = subprocess.CompletedProcess([], 1, "", "No such secret service")
        result = CredentialService().set_token("test-token", remember=True)
        self.assertFalse(result.persisted)
        self.assertIn("Secret Service", result.message)
        self.assertIn("No such secret service", result.message)


if __name__ == "__main__":
    unittest.main()

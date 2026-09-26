from __future__ import annotations

import io
import urllib.error
import unittest
from unittest.mock import patch

from repoflow.services.github_service import GitHubError, GitHubService


class GitHubAuthenticationTests(unittest.TestCase):
    def test_invalid_token_401_has_clear_message(self):
        error = urllib.error.HTTPError(
            url="https://api.github.com/user",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Bad credentials"}'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(GitHubError) as ctx:
                GitHubService("invalid-token").get_user()
        self.assertEqual(ctx.exception.status, 401)
        self.assertIn("rejected this token", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main


class DiscoveryTests(unittest.TestCase):
    @patch.dict(os.environ, {"GITHUB_TOKEN": "writer", "GITHUB_READ_TOKEN": "reader"})
    @patch("app.main.requests.request")
    def test_separate_credentials(self, request):
        main.github("GET", "/user/repos", discovery=True)
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer reader")
        main.github("POST", "/repos/owner/profile/pulls", payload={})
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer writer")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "writer", "GITHUB_READ_TOKEN": ""})
    @patch("app.main.requests.request")
    def test_empty_discovery_token_falls_back(self, request):
        main.github("GET", "/user/repos", discovery=True)
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer writer")

    def test_private_summary_stays_out_of_public_data(self):
        repo = {"owner": {"login": main.OWNER}, "private": True,
                "name": "secret-project", "language": "Python"}
        for enabled, expected in [("true", 1), ("false", 0)]:
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as tmp:
                with patch.object(main, "DATA", Path(tmp)), patch.dict(os.environ, {"PRIVATE_SCAN": enabled}):
                    with patch.object(main, "github", return_value=[repo]) as github:
                        self.assertEqual(main.scan_repos(), [])
                        self.assertTrue(github.call_args.kwargs["discovery"])
                    summary = json.loads((Path(tmp) / "private-summary.json").read_text())
                    self.assertEqual(summary["repository_count"], expected)
                    self.assertEqual(summary["languages_local_only"], {"Python": 1} if expected else {})
                    self.assertNotIn("secret-project", json.dumps(summary))

    def test_private_only_proposal_requires_exact_note(self):
        base = "My profile"
        note = main.language_note(["Python"])
        self.assertEqual(main.validate(base, base + "\n" + note, ["private-languages"], [], ["Python"]), "valid")
        with self.assertRaises(ValueError):
            main.validate(base, "Python expert\n" + note, ["private-languages"], [], ["Python"])
        with self.assertRaises(ValueError):
            main.validate(base, base + "\n" + note, ["private-languages"], [])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test"})
    @patch("app.main.OpenAI")
    def test_model_receives_language_names_only(self, client):
        client.return_value.chat.completions.create.return_value.choices[0].message.content = json.dumps({"readme": "unchanged", "evidence": []})
        main.propose("profile", [], ["Python"])
        payload = json.loads(client.return_value.chat.completions.create.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(payload, {"current_readme": "profile", "public_repository_metadata": [], "approved_language_names": ["Python"]})

    def test_language_sharing_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(main, "DATA", Path(tmp)):
            (Path(tmp) / "private-summary.json").write_text(json.dumps({"repository_count": 3, "languages_local_only": {"Python": 2, "JavaScript": 1}}))
            with patch.dict(os.environ, {"PRIVATE_SCAN": "true", "PRIVATE_LANGUAGES_FOR_PROFILE": "true"}):
                self.assertEqual(main.approved_private_languages(), ["JavaScript", "Python"])
            with patch.dict(os.environ, {"PRIVATE_LANGUAGES_FOR_PROFILE": "false"}):
                self.assertEqual(main.approved_private_languages(), [])
            with patch.dict(os.environ, {"PRIVATE_SCAN": "false", "PRIVATE_LANGUAGES_FOR_PROFILE": "true"}):
                self.assertEqual(main.approved_private_languages(), [])

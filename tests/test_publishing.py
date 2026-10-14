import base64
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from app import main


class PublishingTests(unittest.TestCase):
    def test_publish_routing(self):
        cases = [
            ("true", "false", False, "valid", "push"),
            ("false", "false", False, "valid", "pr"),
            ("true", "true", False, "valid", "preview"),
            ("true", "false", True, "valid", "preview"),
            ("true", "false", False, "unchanged", "none"),
            ("true", "false", False, "insignificant", "none"),
        ]
        for auto, dry, flag, status, expected in cases:
            with self.subTest(case=(auto, dry, flag, status)), tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, {"AUTO_PUSH": auto, "DRY_RUN": dry}))
                stack.enter_context(patch.object(main, "DATA", Path(tmp)))
                stack.enter_context(patch.object(main, "read_profile", return_value=("old", "original-sha")))
                stack.enter_context(patch.object(main, "scan_repos", return_value=[]))
                stack.enter_context(patch.object(main, "approved_private_languages", return_value=[]))
                stack.enter_context(patch.object(main, "propose", return_value={"readme": "new", "evidence": []}))
                stack.enter_context(patch.object(main, "validate", return_value=status))
                push = stack.enter_context(patch.object(main, "push_readme", return_value="commit-url"))
                pr = stack.enter_context(patch.object(main, "create_draft_pr", return_value="pr-url"))
                main.run(dry_run=flag)
                self.assertEqual(push.called, expected == "push")
                self.assertEqual(pr.called, expected == "pr")
                self.assertEqual((Path(tmp) / "proposed-README.md").exists(), expected == "preview")

    @patch.object(main, "github", return_value={"commit": {"html_url": "commit-url"}})
    def test_direct_commit_targets_profile_and_preserves_sha(self, github):
        self.assertEqual(main.push_readme("Caffè", "old-sha"), "commit-url")
        github.assert_called_once_with("PUT", f"/repos/{main.PROFILE}/contents/README.md", payload={
            "message": "docs(profile): refresh README from approved evidence",
            "content": base64.b64encode("Caffè".encode()).decode(),
            "sha": "old-sha", "branch": main.BRANCH})

    @patch.object(main, "github", side_effect=RuntimeError("HTTP 409"))
    def test_conflict_is_not_retried(self, github):
        with self.assertRaisesRegex(RuntimeError, "409"):
            main.push_readme("new", "stale-sha")
        self.assertEqual(github.call_count, 1)

    @patch.object(main, "read_profile")
    def test_invalid_settings_fail_before_api_calls(self, read):
        for variable in ("AUTO_PUSH", "DRY_RUN"):
            with patch.dict(os.environ, {"AUTO_PUSH": "false", "DRY_RUN": "true", variable: "typo"}):
                with self.assertRaises(ValueError):
                    main.run()
        read.assert_not_called()

    @patch.object(main, "BlockingScheduler")
    def test_scheduler_preserves_dry_run_flag(self, scheduler):
        with patch("sys.argv", ["curator", "--dry-run"]):
            main.main()
        self.assertEqual(scheduler.return_value.add_job.call_args.kwargs["kwargs"], {"dry_run": True})

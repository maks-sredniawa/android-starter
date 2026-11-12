"""python3 -m unittest discover -s scripts"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("notes_gate", Path(__file__).with_name("notes-gate.py"))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

GRADLE = 'versionName = "0.2.0" // x-release-please-version\n'
LISTING = "## Release notes\n\n### 0.2.0\n\n### 0.1.0\n"


class Order(unittest.TestCase):
    def test_notes_written_above_their_predecessor_fail_on_the_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.gradle.kts").write_text(GRADLE)
            (root / "store-listing.md").write_text(LISTING)
            with (
                mock.patch.multiple(gate, ROOT=root, GRADLE=root / "build.gradle.kts", LISTING=root / "store-listing.md"),
                mock.patch.object(sys, "argv", ["notes-gate.py"]),
                self.assertRaises(SystemExit) as refused,
            ):
                gate.main()
        self.assertIn("out of order: ### 0.1.0 comes after ### 0.2.0", str(refused.exception.code))


class Pending(unittest.TestCase):
    def pending_in(self, root):
        with (
            mock.patch.multiple(gate, ROOT=root, LISTING=root / "store-listing.md"),
            mock.patch.object(gate, "git") as git,
            mock.patch.object(gate.subprocess, "run", return_value=mock.Mock(returncode=1)) as run,
        ):
            owed = gate.pending("origin/main")
        return owed, git, run

    def test_the_template_itself_owes_no_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts/test_bootstrap.py").write_text("")
            owed, git, run = self.pending_in(root)
        self.assertEqual(owed, 0)
        git.assert_not_called()
        run.assert_not_called()

    def test_an_app_still_holding_bootstrap_py_asks_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bootstrap.py").write_text("")
            owed, git, run = self.pending_in(root)
        self.assertEqual(owed, 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][3:5], ["rev-parse", "--verify"])


if __name__ == "__main__":
    unittest.main()

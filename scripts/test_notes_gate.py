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
    def test_the_template_itself_owes_no_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bootstrap.py").write_text("")
            with mock.patch.object(gate, "ROOT", root), mock.patch.object(gate, "git") as git:
                self.assertEqual(gate.pending("origin/main"), 0)
            git.assert_not_called()


if __name__ == "__main__":
    unittest.main()

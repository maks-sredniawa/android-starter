"""python3 -m unittest discover -s scripts"""

import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("sync_support", Path(__file__).with_name("sync-support.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

GRADLE = 'android {\n    namespace = "app.kettle"\n    defaultConfig {\n        applicationId = "com.maksforge.kettle"\n    }\n}\n'
OLD_STRINGS = """<resources>
    <string name="app_name" translatable="false">Kettle</string>
    <string name="support_title">Old title</string>
    <string name="support_subject_bug" translatable="false">Kettle Brew #bug</string>
    <string name="kettle_own">Mine</string>
</resources>
"""
OLD_HANDOFF = 'package app.kettle.ui.support\n\nprivate const val SUPPORT_ADDRESS = "kettle.help@maksforge.com"\n'


def make_app(root: Path, tip: bool = True) -> Path:
    app = root / "kettle"
    (app / "app/src/main/res/values").mkdir(parents=True)
    (app / "app/src/main/res/values-pl").mkdir()
    (app / "app/src/main/res/values-de").mkdir()
    (app / "app/build.gradle.kts").write_text(GRADLE)
    for values in ["values", "values-pl", "values-de"]:
        (app / f"app/src/main/res/{values}/strings.xml").write_text(OLD_STRINGS)
    support = app / "app/src/main/java/app/kettle/ui/support"
    support.mkdir(parents=True)
    (support / "SupportHandoff.kt").write_text(OLD_HANDOFF)
    if tip:
        (app / "app/src/main/java/app/kettle/tip").mkdir()
    return app


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with mock.patch.object(sys, "argv", ["sync-support.py", *argv]), contextlib.redirect_stdout(out):
        code = sync.main()
    return code, out.getvalue()


class Sync(unittest.TestCase):
    def test_a_first_sync_writes_the_config_from_what_the_app_compiled_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            run(str(app))
            config = (app / "app/src/main/java/app/kettle/ui/support/SupportConfig.kt").read_text()
        self.assertIn('SUPPORT_ADDRESS = "kettle.help@maksforge.com"', config)
        self.assertIn('PLAY_PACKAGE = "com.maksforge.kettle"', config)
        self.assertIn('MAIL_TAG = "Kettle Brew"', config)
        self.assertIn('SITE_URL = "https://maksforge.com/kettle/"', config)
        self.assertIn("package app.kettle.ui.support", config)

    def test_the_site_comes_from_the_remote_not_a_worktrees_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            subprocess.run(["git", "init", "-q", str(app)], check=True)
            subprocess.run(["git", "-C", str(app), "remote", "add", "origin", "git@github.com:owner/kettle-app.git"], check=True)
            run(str(app))
            config = (app / "app/src/main/java/app/kettle/ui/support/SupportConfig.kt").read_text()
        self.assertIn('SITE_URL = "https://maksforge.com/kettle-app/"', config)

    def test_the_module_arrives_in_the_apps_package_and_its_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            config = app / "app/src/main/java/app/kettle/ui/support/SupportConfig.kt"
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text("// the app's own\n")
            run(str(app))
            screen = (app / "app/src/main/java/app/kettle/ui/support/SupportScreen.kt").read_text()
            self.assertEqual(config.read_text(), "// the app's own\n")
            self.assertTrue((app / "app/src/main/java/app/kettle/tip/TipJar.kt").is_file())
        self.assertNotIn("app.starter", screen)
        self.assertIn("import app.kettle.R", screen)

    def test_strings_move_into_the_block_once_and_the_apps_own_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            run(str(app))
            run(str(app))
            base = (app / "app/src/main/res/values/strings.xml").read_text()
            german = (app / "app/src/main/res/values-de/strings.xml").read_text()
        self.assertEqual(base.count(sync.BEGIN), 1)
        self.assertEqual(len(re.findall(r'name="support_title"', base)), 1)
        self.assertNotIn("Old title", base)
        self.assertNotIn("support_subject_bug", base)
        self.assertIn('name="kettle_own"', base)
        self.assertNotIn(sync.BEGIN, german)

    def test_check_reports_drift_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            code, out = run(str(app), "--check")
            self.assertFalse((app / "app/src/main/java/app/kettle/ui/support/SupportScreen.kt").exists())
            self.assertEqual(code, 1)
            self.assertIn("values-de: the template has no translation", out)
            run(str(app))
            self.assertEqual(run(str(app), "--check")[0], 0)

    def test_an_app_without_the_tip_gets_no_tip_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp), tip=False)
            run(str(app))
            support = app / "app/src/main/java/app/kettle/ui/support"
            self.assertFalse((support / "TipSection.kt").exists())
            self.assertFalse((app / "app/src/main/java/app/kettle/tip").exists())
            base = (app / "app/src/main/res/values/strings.xml").read_text()
        self.assertNotIn("support_tip", base)
        self.assertIn('name="support_rate"', base)

    def test_a_kept_file_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(Path(tmp))
            (app / "scripts").mkdir()
            (app / "scripts/support-sync.keep").write_text("ui/support/LicencesScreen.kt\n")
            _, out = run(str(app))
            self.assertFalse((app / "app/src/main/java/app/kettle/ui/support/LicencesScreen.kt").exists())
        self.assertIn("kept the app's own ui/support/LicencesScreen.kt", out)


if __name__ == "__main__":
    unittest.main()

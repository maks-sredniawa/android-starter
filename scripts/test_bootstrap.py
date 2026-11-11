"""python3 -m unittest discover -s scripts"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def bootstrapped_site_config() -> str:
    text = (ROOT / "docs/_config.yml").read_text(encoding="utf-8")
    for old, new in bootstrap.site_config_replacements("Kettle", "kettle"):
        text = text.replace(old, new)
    return text


class SiteConfig(unittest.TestCase):
    def test_template_config_names_its_kind(self):
        self.assertIn("  kind: Template\n", (ROOT / "docs/_config.yml").read_text(encoding="utf-8"))

    def test_new_app_config_has_no_kind_line(self):
        self.assertNotRegex(bootstrapped_site_config(), r"(?m)^\s*kind:")

    def test_new_app_config_names_the_app_and_its_status(self):
        config = bootstrapped_site_config()
        self.assertIn("title: Kettle\n", config)
        self.assertIn("icon: /assets/icons/kettle.webp\n", config)
        self.assertIn("status: building\n", config)


if __name__ == "__main__":
    unittest.main()

"""python3 -m unittest discover -s scripts"""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("aab_locale", Path(__file__).with_name("aab-locale.py"))
aab_locale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aab_locale)


def table_of(*values):
    return b"\x12\x03pad" + b"".join(aab_locale.field(value) for value in values) + b"\x1a\x00"


class WholeField(unittest.TestCase):
    def test_a_value_only_inside_a_longer_one_is_missing(self):
        table = table_of("Pomoc i opinie")
        self.assertIn(b"Pomoc", table)
        self.assertEqual(aab_locale.missing_from(table, {"credits_helped_by": "Pomoc"}), [("credits_helped_by", "Pomoc")])

    def test_a_whole_value_is_present(self):
        table = table_of("Pomoc i opinie", "Pomoc")
        self.assertEqual(aab_locale.missing_from(table, {"credits_helped_by": "Pomoc"}), [])

    def test_a_value_over_127_bytes_takes_a_two_byte_length(self):
        value = "ż" * 100
        self.assertEqual(aab_locale.field(value)[:3], b"\x0a\xc8\x01")
        self.assertEqual(aab_locale.missing_from(table_of(value), {"long": value}), [])
        self.assertEqual(aab_locale.missing_from(table_of(value + "!"), {"long": value}), [("long", value)])


if __name__ == "__main__":
    unittest.main()

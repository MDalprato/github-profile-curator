import unittest
from unittest.mock import patch
from app.main import validate

BASE = "## Toolkit (spells and gadgets)\n" + "A" * 500 + "\n## Terminal stats\n"
PUBLIC = [{"url": "https://github.com/MDalprato/demo"}]

class ValidationTests(unittest.TestCase):
    def test_unchanged(self):
        self.assertEqual(validate(BASE, BASE, [], PUBLIC), "unchanged")

    def test_rejects_missing_evidence(self):
        with self.assertRaises(ValueError):
            validate(BASE, BASE + "\nNew project is cool!\n", [], PUBLIC)

    def test_rejects_unknown_link(self):
        with self.assertRaises(ValueError):
            validate(BASE, BASE + "\nNew project https://example.com/untrusted\n", [PUBLIC[0]["url"]], PUBLIC)

    def test_rejects_dropped_sections(self):
        with self.assertRaises(ValueError):
            validate(BASE, "x" * 400, [PUBLIC[0]["url"]], PUBLIC)

if __name__ == "__main__":
    unittest.main()

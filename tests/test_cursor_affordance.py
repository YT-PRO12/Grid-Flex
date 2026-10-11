import unittest
from pathlib import Path


class CursorAffordanceTests(unittest.TestCase):
    def test_read_only_labels_use_arrow_and_controls_have_pointer(self):
        css = (Path(__file__).resolve().parents[1] / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("body, body * { cursor: default; }", css)
        self.assertIn("a[href], a[href] *", css)
        self.assertIn("button:not(:disabled)", css)
        self.assertIn('input[type="range"]', css)
        self.assertIn('textarea, [contenteditable="true"]', css)


if __name__ == "__main__":
    unittest.main()

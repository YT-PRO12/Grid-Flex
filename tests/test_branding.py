"""Guard the precise public product name requested by the project owner."""
import unittest
from pathlib import Path
from app import status_payload

ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_api_name_is_grid_flex(self):
        self.assertEqual(status_payload()["name"], "Grid Flex")

    def test_user_facing_sources_do_not_use_old_brand(self):
        for rel in ("web/index.html", "web/app.js", "start-local.ps1", "README.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("GridFlex AI", text, rel)
            self.assertNotIn("GRIDFLEX AI", text, rel)

    def test_html_title_uses_new_brand(self):
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Grid Flex —", html)


if __name__ == "__main__":
    unittest.main()

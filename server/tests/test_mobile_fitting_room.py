"""Mobile fitting-room contracts. Static, stdlib, no browser or API calls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "virtual-closet" / "app" / "app.js").read_text()
HTML = (ROOT / "virtual-closet" / "app" / "index.html").read_text()
CSS = (ROOT / "virtual-closet" / "app" / "style.css").read_text()


class TestMobileOutfitPath(unittest.TestCase):
    def test_mobile_controls_are_real_named_controls(self):
        self.assertIn('class="row-add', APP)
        self.assertIn('id="mobile-outfit-jump"', HTML)
        self.assertIn('id="outfit-mobile-note"', HTML)

    def test_add_control_cannot_generate_or_preview(self):
        """Adding to a slot is intentionally cheaper than trying an item on."""
        start = APP.index("function toggleOutfitItem")
        end = APP.index("/* ── drag-to-dress", start)
        body = APP[start:end]
        self.assertNotIn("fetch(", body)
        self.assertNotIn("tryOn(", body)
        self.assertNotIn("generateRender(", body)

    def test_add_button_does_not_bubble_into_row_try_on_or_drag(self):
        self.assertIn("e.stopPropagation();\n      toggleOutfitItem", APP)
        self.assertIn('if (!e.target.closest(".row-add")) beginRowDrag', APP)

    def test_generation_stays_behind_named_outfit_action(self):
        start = APP.index('$("#render-outfit").addEventListener')
        end = APP.index("function toast", start)
        handler = APP[start:end]
        self.assertIn('fetch("/api/generate"', handler)
        self.assertIn("if (!M.generation_enabled)", handler)

    def test_mobile_targets_and_desktop_hiding_are_pinned(self):
        self.assertIn(".row-add { display: none; }", CSS)
        self.assertIn("min-height: 44px", CSS)
        self.assertIn("#mobile-outfit-jump[hidden] { display: none; }", CSS)


if __name__ == "__main__":
    unittest.main()

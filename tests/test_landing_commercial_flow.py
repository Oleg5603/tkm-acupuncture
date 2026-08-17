from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "landing"
INDEX = LANDING / "index.html"


class LandingCommercialFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_full_archive_is_not_published_in_webroot(self):
        published = [
            path
            for path in LANDING.rglob("*")
            if path.is_file()
            and "full" in path.name.lower()
            and path.suffix.lower() == ".zip"
        ]
        self.assertEqual([], published, f"Full archives exposed in landing: {published}")

    def test_no_direct_full_download_url(self):
        self.assertNotIn("TKM-full.zip", self.html)
        self.assertNotIn('data-dl="full"', self.html)
        self.assertNotIn('id="fullDownloadLink"', self.html)

    def test_no_fake_automatic_payment_confirmation(self):
        forbidden = (
            "Оплата подтверждена",
            "откроется автоматически",
            "Проверяем платёж, подождите несколько секунд",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, self.html)
        self.assertNotRegex(self.html, r"setTimeout\s*\(")

    def test_manual_fulfilment_is_disclosed(self):
        self.assertIn("вручную проверим платёж", self.html)
        self.assertIn("персональную ссылку", self.html)

    def test_order_capture_fails_closed(self):
        self.assertIn("await fetch('save-email.php'", self.html)
        self.assertIn("!response.ok", self.html)
        self.assertIn("data.ok !== true", self.html)
        self.assertIn("!data.order_id", self.html)
        self.assertNotIn("не блокируем демонстрацию оплаты", self.html)


if __name__ == "__main__":
    unittest.main()

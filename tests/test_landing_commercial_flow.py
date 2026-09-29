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

    def test_github_pages_flow_does_not_call_php(self):
        self.assertNotIn("fetch('save-email.php'", self.html)
        self.assertNotIn("fetch('feedback.php'", self.html)
        self.assertNotIn("fetch('count.php", self.html)
        self.assertIn('href="mailto:ogp56@bk.ru', self.html)

    def test_public_page_does_not_expose_payment_credentials(self):
        self.assertNotIn("5536 9141 5967 4112", self.html)
        self.assertNotIn("assets/payment-qr.png", self.html)

    def test_accessibility_and_trust_basics(self):
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('aria-label="Основная навигация"', self.html)
        self.assertIn('id="trust"', self.html)
        self.assertIn("Вспомогательный инструмент", self.html)

    def test_demo_request_has_no_broken_local_archive_link(self):
        self.assertNotIn("assets/downloads/TKM-demo.zip", self.html)
        self.assertIn("Получить демо", self.html)


if __name__ == "__main__":
    unittest.main()

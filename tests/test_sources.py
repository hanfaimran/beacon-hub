import unittest
from app.sources import get_source_domain, is_trusted


class TestSources(unittest.TestCase):
    def test_trusted_domain_exact(self):
        self.assertTrue(is_trusted("https://aws.amazon.com/certification/"))

    def test_trusted_domain_subdomain(self):
        self.assertTrue(is_trusted("https://sub.github.com/repo"))

    def test_lookalike_domain(self):
        self.assertFalse(is_trusted("https://aws.amazon.com.evil.com/phishing"))

    def test_untrusted_domain(self):
        self.assertFalse(is_trusted("https://untrusted-domain.org"))

    def test_get_source_domain_basic(self):
        self.assertEqual(get_source_domain("https://learn.microsoft.com/docs"), "learn.microsoft.com")

    def test_get_source_domain_with_port(self):
        self.assertEqual(get_source_domain("http://kaggle.com:8080/competitions"), "kaggle.com")


if __name__ == "__main__":
    unittest.main()

import unittest
from app.extract import normalize_url, extract_candidate_dates

class TestExtract(unittest.TestCase):
    def test_normalize_url(self):
        url = "https://example.com/event/?utm_source=google&gclid=12345/"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://example.com/event")

    def test_extract_candidate_dates(self):
        text = "Join us on October 20, 2026 for the main hackathon event. Registration closes October 12, 2026."
        candidates = extract_candidate_dates(text)
        self.assertTrue(len(candidates) >= 2)
        matched_strings = [c["matched_str"] for c in candidates]
        self.assertIn("October 20, 2026", matched_strings)
        self.assertIn("October 12, 2026", matched_strings)

if __name__ == "__main__":
    unittest.main()

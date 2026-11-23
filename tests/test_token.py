import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_token  # noqa: E402


class TokenTests(unittest.TestCase):
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)

    def test_parses_github_header_formats(self):
        self.assertEqual(check_token.parse_expiry('2026-12-22 15:00:00 UTC'),
                         datetime(2026, 12, 22, 15, tzinfo=timezone.utc))
        self.assertEqual(check_token.parse_expiry('2026-12-23 00:00:00 +0900'),
                         datetime(2026, 12, 22, 15, tzinfo=timezone.utc))
        self.assertIsNone(check_token.parse_expiry(None))

    def test_alerts_within_14_days_or_when_rejected(self):
        far = datetime(2026, 12, 22, tzinfo=timezone.utc)
        self.assertFalse(check_token.evaluate(200, far, self.now)[0])
        self.assertTrue(check_token.evaluate(200, far, datetime(2026, 12, 10, tzinfo=timezone.utc))[0])
        self.assertTrue(check_token.evaluate(401, None, self.now)[0])
        self.assertFalse(check_token.evaluate(200, None, self.now)[0])  # no expiry
        self.assertFalse(check_token.evaluate(502, None, self.now)[0])  # unknown, retry tomorrow

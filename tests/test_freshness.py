import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_freshness as fresh  # noqa: E402
import refresh_snapshot  # noqa: E402


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        # Friday 2026-11-20 is the latest completed session as of Sunday.
        self.sessions = refresh_snapshot.completed_sessions('2026-11-22T06:00:00Z')

    def test_lag_counts_sessions_not_calendar_days(self):
        self.assertEqual(fresh.lag('2026-11-20', self.sessions), 0)
        self.assertEqual(fresh.lag('2026-11-19', self.sessions), 1)
        self.assertEqual(fresh.lag('2026-11-18', self.sessions), 2)

    def test_one_session_behind_is_normal_two_is_stale(self):
        stale, _ = fresh.evaluate({'a': '2026-11-19', 'b': '2026-11-20'}, self.sessions)
        self.assertFalse(stale)
        stale, lines = fresh.evaluate({'a': '2026-11-18', 'b': '2026-11-20'}, self.sessions)
        self.assertTrue(stale)
        self.assertIn('| a | 2026-11-18 | 2 |', lines)

    def test_unreachable_site_counts_as_stale(self):
        stale, lines = fresh.evaluate({'a': None}, self.sessions)
        self.assertTrue(stale)
        self.assertIn('| a | unreachable | — |', lines)

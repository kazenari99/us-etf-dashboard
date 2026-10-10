import sys
import unittest
import io
import json
import tempfile
from unittest.mock import patch
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_stocks import previous_tokyo_session, matches, validate
import refresh_stocks


class StocksTests(unittest.TestCase):
    def test_tokyo_previous_day_holidays_and_dst(self):
        for clock, expected in [
            ('2026-10-10T07:00:00+09:00', '2026-10-09'),
            ('2026-10-11T07:00:00+09:00', None),
            ('2026-10-12T07:00:00+09:00', None),
            ('2026-09-08T07:00:00+09:00', None),
            ('2026-01-06T07:00:00+09:00', '2026-01-05'),
            ('2026-11-28T07:00:00+09:00', '2026-11-27')]:
            self.assertEqual(previous_tokyo_session(datetime.fromisoformat(clock)), expected)

    def test_exact_filter_and_missing_values(self):
        row = dict(rs_rating=90, below_52w_high_pct=25, volume_ratio=1)
        self.assertTrue(matches(row))
        for field, bad in [('rs_rating', 89), ('below_52w_high_pct', 25.01), ('volume_ratio', .999),
                           ('volume_ratio', None), ('rs_rating', float('nan')), ('volume_ratio', True)]:
            self.assertFalse(matches(dict(row, **{field: bad})))

    def test_snapshot_integrity(self):
        valid = dict(session_date='2026-10-09', count=1, stocks=[{'ticker':'TXG'}])
        self.assertEqual(validate(valid), valid)
        for bad in [dict(valid, count=2), dict(valid, stocks=[]),
                    dict(valid, count=2, stocks=[{'ticker':'TXG'}, {'ticker':'TXG'}])]:
            with self.assertRaises(ValueError):
                validate(bad)

    def test_failed_source_keeps_latest_deployed_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            old = dict(session_date='2026-10-08', count=1, stocks=[{'ticker':'TXG'}], fetched_at='2026-10-09T01:00:00Z')
            deployed = dict(old, session_date='2026-10-09', fetched_at='2026-10-10T01:00:00Z')
            (root / 'dist/stocks.json').write_text(json.dumps(old))
            (root / 'dist/snapshot_meta.json').write_text(json.dumps({'asof':'2026-10-09'}))
            with patch.object(refresh_stocks, 'ROOT', root), patch.object(refresh_stocks, 'urlopen', side_effect=[io.StringIO(json.dumps(deployed)), OSError('offline')]):
                refresh_stocks.refresh()
            result = json.loads((root / 'dist/stocks.json').read_text())
            self.assertEqual(result['session_date'], '2026-10-09')
            self.assertEqual(result['fetched_at'], deployed['fetched_at'])
            self.assertEqual(result['fetch_status'], 'failed')

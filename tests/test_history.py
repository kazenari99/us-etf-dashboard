import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import record_history  # noqa: E402


def write_snapshot(root, asof, generated_at, body=b'ticker,score\nSPY,50\n', sha=None):
    folder = root / asof / generated_at.replace(':', '')
    folder.mkdir(parents=True)
    (folder / 'etf_momentum_latest.csv').write_bytes(body)
    meta = {'asof': asof, 'generated_at': generated_at, 'count': 1,
            'sha256': sha or hashlib.sha256(body).hexdigest(), 'model': 'm', 'source': 's'}
    (folder / 'snapshot_meta.json').write_text(json.dumps(meta))


class HistoryTests(unittest.TestCase):
    def test_records_latest_snapshot_and_keeps_sorted_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            history = tmp / 'history'
            write_snapshot(tmp / 'a', '2026-11-20', '2026-11-21T00:00:00')
            record_history.record(tmp / 'a', history)
            write_snapshot(tmp / 'b', '2026-11-19', '2026-11-20T00:00:00')
            write_snapshot(tmp / 'b', '2026-11-19', '2026-11-20T06:00:00', body=b'ticker,score\nSPY,51\n')
            (tmp / 'b' / 'fund_profiles').mkdir()
            self.assertEqual(record_history.record(tmp / 'b', history), '2026-11-19')
            self.assertEqual((history / 'etf/2026-11-19.csv').read_bytes(), b'ticker,score\nSPY,51\n')
            index = list(csv.DictReader((history / 'etf/index.csv').open()))
            self.assertEqual([r['asof'] for r in index], ['2026-11-19', '2026-11-20'])
            # Re-recording a session replaces it instead of duplicating it.
            record_history.record(tmp / 'a', history)
            self.assertEqual(len(list(csv.DictReader((history / 'etf/index.csv').open()))), 2)

    def test_checksum_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_snapshot(tmp / 'a', '2026-11-20', '2026-11-21T00:00:00', sha='0' * 64)
            with self.assertRaises(SystemExit):
                record_history.record(tmp / 'a', tmp / 'history')
            self.assertFalse((tmp / 'history/etf/2026-11-20.csv').exists())

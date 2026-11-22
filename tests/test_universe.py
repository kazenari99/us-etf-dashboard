import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from momentum import UNIVERSE  # noqa: E402


class UniverseTests(unittest.TestCase):
    def setUp(self):
        self.tickers = [t for tickers in UNIVERSE.values() for t in tickers.split()]
        self.app = (ROOT / 'dist/app.js').read_text()
        self.i18n = (ROOT / 'dist/i18n.js').read_text()

    def test_each_ticker_once_and_benchmark_present(self):
        self.assertEqual(len(self.tickers), len(set(self.tickers)))
        self.assertIn('SPY', self.tickers)

    def test_every_group_and_ticker_has_translated_labels(self):
        groups = dict(re.findall(r"(\w+):'([^']+)'", re.search(r'const groupNames = \{(.*?)\};', self.app).group(1)))
        names = dict(re.findall(r'"([A-Z]+)": "([^"]+)"', self.app))
        for group in UNIVERSE:
            with self.subTest(group=group):
                self.assertIn(group, groups)
                self.assertIn(f"['{groups[group]}',", self.i18n)
        for ticker in self.tickers:
            with self.subTest(ticker=ticker):
                self.assertIn(ticker, names)
                self.assertIn(f"['{names[ticker]}',", self.i18n)


class ValidateSnapshotTests(unittest.TestCase):
    def test_tampered_csv_fails_checksum_without_assert(self):
        import shutil
        import tempfile
        import validate_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            for name in ('etf_momentum_latest.csv', 'snapshot_meta.json'):
                shutil.copy(ROOT / 'dist' / name, dist / name)
            validate_snapshot.validate(dist)
            with (dist / 'etf_momentum_latest.csv').open('a') as out:
                out.write('\n')
            with self.assertRaisesRegex(validate_snapshot.SnapshotError, 'Checksum mismatch'):
                validate_snapshot.validate(dist)

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

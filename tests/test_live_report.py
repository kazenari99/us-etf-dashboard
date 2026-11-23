import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import live_report  # noqa: E402


def write_snapshots(root, n, predictive, seed=4):
    rng = np.random.default_rng(seed)
    tickers = ['SPY'] + [f'E{i:02d}' for i in range(39)]
    drift = {t: rng.normal(0, 0.003) for t in tickers}
    drift['SPY'] = 0.0
    price = {t: 100.0 for t in tickers}
    (root / 'etf').mkdir(parents=True)
    for d in pd.bdate_range('2026-01-05', periods=n):
        for t in tickers:
            price[t] *= 1 + drift[t] + rng.normal(0, 0.01)
        # A predictive score ranks by the true drift; otherwise it is noise.
        score = {t: (drift[t] if predictive else rng.normal()) for t in tickers}
        pd.DataFrame({'ticker': tickers, 'score': [score[t] for t in tickers],
                      'close': [price[t] for t in tickers]}).to_csv(root / 'etf' / f'{d.date()}.csv', index=False)


class LiveReportTests(unittest.TestCase):
    def test_not_enough_data_is_said_plainly(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_snapshots(Path(tmp), 12, predictive=True)
            text = live_report.report(live_report.load(Path(tmp)))
        self.assertIn('Not enough data yet', text)
        self.assertNotIn('Top 10 beat SPY', text)

    def test_predictive_scores_show_up_as_excess_return_and_ic(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_snapshots(Path(tmp), 260, predictive=True)
            snaps = live_report.load(Path(tmp))
            rows = live_report.forward(snaps, 20, step=20)
            self.assertGreater((rows.top - rows.spy).mean(), 0)
            self.assertGreater(live_report.forward(snaps, 5, step=1).ic.mean(), 0.1)
            self.assertIn('Top 10 beat SPY', live_report.report(snaps))

    def test_random_scores_show_no_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_snapshots(Path(tmp), 260, predictive=False)
            ic = live_report.forward(live_report.load(Path(tmp)), 5, step=1).ic.mean()
        self.assertLess(abs(ic), 0.05)

    def test_uses_closes_from_both_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'etf'
            root.mkdir()
            for i, d in enumerate(pd.bdate_range('2026-01-05', periods=6)):
                pd.DataFrame({'ticker': ['SPY', 'A'], 'score': [0, 1],
                              'close': [100, 100 * (1.01 ** i)]}).to_csv(root / f'{d.date()}.csv', index=False)
            rows = live_report.forward(live_report.load(Path(tmp)), 5, step=5)
        self.assertAlmostEqual(rows.iloc[0].spy, 0.0)
        self.assertAlmostEqual(rows.iloc[0].ew, (1.01 ** 5 - 1) / 2)

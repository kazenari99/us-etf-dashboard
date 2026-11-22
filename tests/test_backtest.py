import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import backtest  # noqa: E402


def synthetic(tickers, days=420, seed=1):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range('2023-01-02', periods=days)
    frames = {}
    for i, ticker in enumerate(tickers):
        drift = 0.0004 * (i - len(tickers) / 2)
        close = 100 * np.exp(np.cumsum(drift + 0.01 * rng.standard_normal(days)))
        frames[ticker] = pd.DataFrame({'open': close, 'high': close * 1.01, 'low': close * 0.99,
                                       'close': close, 'volume': 1e6}, index=index)
    return frames


class BacktestTests(unittest.TestCase):
    def test_weights_apply_after_lag_and_pay_costs(self):
        index = pd.bdate_range('2026-01-05', periods=5)
        returns = pd.DataFrame({'A': [0.0, 0.10, 0.10, 0.10, 0.10]}, index=index)
        weights = pd.DataFrame({'A': [1.0]}, index=index[:1])
        r = backtest.portfolio(weights, returns)
        # Decided at close of day 0, bought at close of day 1, first return on day 2.
        self.assertEqual(r.iloc[1], 0.0)
        self.assertAlmostEqual(r.iloc[2], 0.10 - backtest.COST)
        self.assertAlmostEqual(r.iloc[3], 0.10)

    def test_end_to_end_report_on_synthetic_prices(self):
        tickers = ['SPY', 'QQQ', 'IWM', 'XLK', 'XLE', 'GLD', 'TLT', 'BIL', 'EEM', 'SMH', 'XBI', 'IBB']
        frames = synthetic(tickers)
        spy = frames['SPY'].index
        dates = backtest.rebalance_dates(spy[spy >= spy[backtest.MIN_BARS]])[:20]
        sig = backtest.signals(frames, dates)
        self.assertEqual(sig['date'].nunique(), 20)
        self.assertTrue(np.isfinite(sig[['score', 'score_risk', 'score_group']].to_numpy()).all())
        text = backtest.report(frames, sig, [3], '2023-01-02')
        for needle in ('Current score, top 3', 'Risk-adjusted ranks, top 3', 'BIL when SPY < 200d', 'Rank IC'):
            self.assertIn(needle, text)
        self.assertNotIn('nan%', text)

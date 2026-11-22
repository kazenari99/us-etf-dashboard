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

    def test_trend_mask_moves_slot_to_cash_with_lag(self):
        index = pd.bdate_range('2026-01-05', periods=6)
        returns = pd.DataFrame({'A': [0.0, 0.0, 0.10, 0.10, 0.10, 0.10]}, index=index)
        weights = pd.DataFrame({'A': [1.0]}, index=index[:1])
        mask = pd.DataFrame({'A': [True, True, False, False, True, True]}, index=index)
        r = backtest.portfolio(weights, returns, mask=mask)
        # Bought at close of day 1 (cost booked on day 2, the first day held).
        self.assertAlmostEqual(r.iloc[2], 0.10 - backtest.COST)
        # Down-cross seen at close of day 2 -> still held on day 3, sold at its close.
        self.assertAlmostEqual(r.iloc[3], 0.10)
        self.assertAlmostEqual(r.iloc[4], -backtest.COST)
        # Up-cross at close of day 4 -> bought at close of day 5, so day 5 is still flat.
        self.assertAlmostEqual(r.iloc[5], 0.0)

    def test_ema_trend_flags_uptrend_after_warmup(self):
        index = pd.bdate_range('2026-01-05', periods=40)
        close = pd.DataFrame({'UP': np.linspace(100, 140, 40), 'DOWN': np.linspace(140, 100, 40)}, index=index)
        trend = backtest.ema_trend(close)
        self.assertFalse(trend.iloc[:19].any().any())
        self.assertTrue(trend['UP'].iloc[-1])
        self.assertFalse(trend['DOWN'].iloc[-1])

    def test_long_momentum_skips_last_month_and_needs_a_year(self):
        index = pd.bdate_range('2024-01-01', periods=300)
        prices = np.linspace(100, 200, 300)
        prices[-21:] = 50  # a crash inside the skipped month must not change 12-1
        close = pd.DataFrame({'A': prices}, index=index)
        mom = backtest.long_momentum(close)
        self.assertTrue(np.isnan(mom['12-1']['A'].iloc[251]))
        expected = prices[-1 - backtest.SKIP] / prices[-1 - 252] - 1
        self.assertAlmostEqual(mom['12-1']['A'].iloc[-1], expected)

    def test_absolute_filter_swaps_laggards_for_cash(self):
        date = pd.Timestamp('2026-01-30')
        scores = pd.DataFrame({'A': [3.0], 'B': [2.0], 'BIL': [1.0]}, index=[date])
        absolute = pd.DataFrame({'A': [0.10], 'B': [0.01], 'BIL': [0.04]}, index=[date])
        w = backtest.pick_top(scores, [date], 2, absolute=absolute)
        self.assertEqual(w.loc[date].to_dict(), {'A': 0.5, 'BIL': 0.5})

    def test_newey_west_matches_plain_t_without_lags_and_shrinks_with_overlap(self):
        rng = np.random.default_rng(0)
        x = 0.1 + rng.standard_normal(500)
        plain = x.mean() / (x.std() / np.sqrt(len(x)))
        self.assertAlmostEqual(backtest.nw_tstat(x, 0), plain)
        # Overlapping sums of iid noise: plain t is inflated, Newey-West corrects it down.
        overlapped = np.convolve(x, np.ones(4), 'valid')
        naive = overlapped.mean() / (overlapped.std() / np.sqrt(len(overlapped)))
        self.assertLess(backtest.nw_tstat(overlapped, 3), naive * 0.7)
        self.assertEqual(backtest.overlap_lags(20, 5), 3)
        self.assertEqual(backtest.overlap_lags(5, 5), 0)
        self.assertEqual(backtest.overlap_lags(21, 21), 0)

    def test_end_to_end_report_on_synthetic_prices(self):
        tickers = ['SPY', 'QQQ', 'IWM', 'XLK', 'XLE', 'GLD', 'TLT', 'BIL', 'EEM', 'SMH', 'XBI', 'IBB']
        frames = synthetic(tickers)
        spy = frames['SPY'].index
        dates = backtest.rebalance_dates(spy[spy >= spy[backtest.MIN_BARS]])[:20]
        sig = backtest.signals(frames, dates)
        self.assertEqual(sig['date'].nunique(), 20)
        self.assertTrue(np.isfinite(sig[['score', 'score_risk', 'score_group']].to_numpy()).all())
        text = backtest.report(frames, sig, [3], '2023-01-02')
        for needle in ('Current score, top 3', 'Risk-adjusted ranks, top 3', 'BIL when SPY < 200d', 'Rank IC',
                       'Current score, top 3, EMA5 > EMA20', 'SPY, EMA5 > EMA20 only', 't vs SPY', 'Newey-West'):
            self.assertIn(needle, text)
        self.assertNotIn('nan%', text)

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_sources  # noqa: E402
import refresh_snapshot as refresh  # noqa: E402
import sources  # noqa: E402


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.sessions = refresh.completed_sessions('2026-09-23T23:37:00Z')

    def stooq_csv(self, scale=1.0):
        rows = ['Date,Open,High,Low,Close,Volume']
        for i, d in enumerate(self.sessions):
            c = (100 + i * 0.1) * scale
            rows.append(f'{d.date()},{c},{c * 1.01},{c * 0.99},{c},1000')
        return '\n'.join(rows) + '\n'

    def test_stooq_csv_passes_production_validation(self):
        raw = sources.parse_stooq(self.stooq_csv(), 'SPY')
        self.assertEqual(len(refresh.normalize(raw, self.sessions, 'SPY')), len(self.sessions))

    def test_stooq_plain_text_errors_are_rejected(self):
        for text in ('No data', 'Exceeded the daily hits limit', ''):
            with self.assertRaises(ValueError):
                sources.parse_stooq(text, 'SPY')

    def test_fallback_only_when_enabled_and_never_for_pending(self):
        calls = []

        def fake_fetch_all(sessions, fetch=None):
            calls.append(fetch)
            if fetch is None:
                raise RuntimeError('Incomplete universe; keeping deployed snapshot')
            return {'SPY': 'frame'}

        published = []
        with patch.object(refresh, 'fetch_all', fake_fetch_all), \
             patch.object(refresh, 'publish_snapshot', lambda f, s, src=None: published.append(src)), \
             patch.object(refresh, 'completed_sessions', lambda: self.sessions):
            with patch.dict(os.environ, {'FALLBACK_SOURCE': ''}):
                with self.assertRaises(RuntimeError):
                    refresh.main()
            with patch.dict(os.environ, {'FALLBACK_SOURCE': 'stooq', 'GITHUB_OUTPUT': ''}):
                refresh.main()
        self.assertEqual(published, [sources.SOURCES['stooq']])
        self.assertIs(calls[-1], sources.FETCHERS['stooq'])

        def pending(sessions, fetch=None):
            calls.append(fetch)
            raise refresh.SnapshotPending('bar not published')

        calls.clear()
        with patch.object(refresh, 'fetch_all', pending), \
             patch.object(refresh, 'completed_sessions', lambda: self.sessions), \
             patch.dict(os.environ, {'FALLBACK_SOURCE': 'stooq', 'GITHUB_STEP_SUMMARY': ''}):
            refresh.main()  # deferred, not a failure
        self.assertEqual(calls, [None])  # a pending Yahoo bar never triggers the fallback

    def test_parity_verdict(self):
        tickers = ['SPY', 'QQQ', 'IWM', 'DIA', 'MDY', 'RSP', 'XLK', 'XLE', 'GLD', 'TLT', 'EEM', 'BIL']
        rng = np.random.default_rng(2)
        yahoo = {}
        for i, t in enumerate(tickers):
            c = 100 * np.exp(np.cumsum(0.0005 * (i - 5) + 0.01 * rng.standard_normal(260)))
            yahoo[t] = pd.DataFrame({'time_key': pd.bdate_range('2025-01-01', periods=260), 'open': c,
                                     'high': c * 1.01, 'low': c * 0.99, 'close': c, 'volume': 1e6})
        with patch.object(check_sources, 'TICKERS', set(tickers)):
            _, ok = check_sources.compare(yahoo, yahoo)
            self.assertTrue(ok)
            # A source that drifts 5% over the window (e.g. missing dividends) is rejected.
            drift = {t: f.assign(close=f['close'] * np.linspace(1.0, 1.05, 260)) for t, f in yahoo.items()}
            _, ok = check_sources.compare(yahoo, drift)
            self.assertFalse(ok)
            # Missing ETFs from the backup source is rejected too.
            _, ok = check_sources.compare(yahoo, {t: yahoo[t] for t in tickers[:-1]})
            self.assertFalse(ok)

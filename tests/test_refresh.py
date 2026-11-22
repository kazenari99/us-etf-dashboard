import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import refresh_snapshot as refresh
from momentum import metrics

class RefreshTests(unittest.TestCase):
    def test_holiday_weekend_dst_and_early_close(self):
        cases = {'2026-09-07T23:37:00Z':'2026-09-04',
                 '2026-09-06T23:37:00Z':'2026-09-04',
                 '2026-03-09T20:59:00Z':'2026-03-06',
                 '2026-03-09T21:01:00Z':'2026-03-09',
                 '2026-01-05T21:59:00Z':'2026-01-02',
                 '2026-11-27T18:59:00Z':'2026-11-25',
                 '2026-11-27T19:01:00Z':'2026-11-27'}
        for now, expected in cases.items():
            with self.subTest(now=now):
                self.assertEqual(str(refresh.completed_sessions(now)[-1].date()), expected)

    def raw(self):
        self.sessions = refresh.completed_sessions('2026-09-23T23:37:00Z')
        return pd.DataFrame({'Open':10., 'High':11., 'Low':9., 'Close':10., 'Volume':100.},
                            index=self.sessions.tz_localize('America/New_York'))

    def test_complete_history(self):
        raw = self.raw()
        self.assertEqual(len(refresh.normalize(raw, self.sessions, 'SPY')), len(self.sessions))

    def test_missing_duplicate_and_stale_sessions(self):
        raw = self.raw()
        for broken in (raw.iloc[:-1], raw.drop(raw.index[10]), pd.concat([raw, raw.iloc[-1:]])):
            with self.assertRaises(ValueError):
                refresh.normalize(broken, self.sessions, 'SPY')

    def test_unfinished_future_bar_discarded(self):
        raw = self.raw()
        future = raw.iloc[-1:].copy()
        future.index += pd.Timedelta(days=1)
        self.assertEqual(len(refresh.normalize(pd.concat([raw, future]), self.sessions, 'SPY')), len(raw))

    def test_invalid_ohlcv(self):
        for key, value in (('Close',np.nan), ('High',1), ('Volume',0), ('Low',-1)):
            raw = self.raw()
            raw.iloc[-1, raw.columns.get_loc(key)] = value
            with self.assertRaises(ValueError):
                refresh.normalize(raw, self.sessions, 'SPY')

    def test_failed_fetch_requires_complete_universe(self):
        with patch.object(refresh, 'TICKERS', {'SPY'}), patch.object(refresh.yf, 'Ticker') as ticker, patch.object(refresh.time, 'sleep'), patch.object(refresh.yf, 'set_tz_cache_location'):
            ticker.return_value.history.side_effect = RuntimeError('temporary unavailable')
            with self.assertRaisesRegex(RuntimeError, 'keeping deployed snapshot'):
                refresh.fetch_all(refresh.completed_sessions('2026-09-23T23:37:00Z'))
            self.assertEqual(ticker.return_value.history.call_count, 3)

    def test_invalid_values_report_date_and_field(self):
        raw = self.raw()
        raw.iloc[-1, raw.columns.get_loc('Close')] = np.nan
        with self.assertRaisesRegex(ValueError, '2026-09-23 close=nan'):
            refresh.normalize(raw, self.sessions, 'SPY')

    def test_unfilled_latest_bar_is_pending_not_corrupt(self):
        raw = self.raw()
        raw.iloc[-1, [raw.columns.get_loc(c) for c in ('Open', 'High', 'Low', 'Close')]] = np.nan
        with self.assertRaisesRegex(refresh.LatestBarPending, '2026-09-23 bar not published'):
            refresh.normalize(raw, self.sessions, 'SPY')
        with self.assertRaises(refresh.LatestBarPending):
            refresh.normalize(raw.iloc[:-1], self.sessions, 'SPY')
        # A NaN inside the history is still corruption, not a pending bar.
        raw.iloc[5, raw.columns.get_loc('Close')] = np.nan
        with self.assertRaises(ValueError) as caught:
            refresh.normalize(raw, self.sessions, 'SPY')
        self.assertNotIsInstance(caught.exception, refresh.LatestBarPending)

    def pending_fetch(self, ready_after):
        complete = self.raw()
        calls = []
        def fetch(ticker, sessions):
            calls.append(ticker)
            return complete if len(calls) > ready_after else complete.iloc[:-1]
        return fetch, calls

    def test_pending_latest_bar_waits_then_defers(self):
        fetch, calls = self.pending_fetch(ready_after=99)
        waits = []
        with patch.object(refresh, 'TICKERS', {'SPY'}), patch.object(refresh.yf, 'set_tz_cache_location'):
            with self.assertRaisesRegex(refresh.SnapshotPending, 'not published the 2026-09-23 bar'):
                refresh.fetch_all(self.sessions, waits=(90, 180), sleep=waits.append, fetch=fetch)
        self.assertEqual(len(calls), 5)
        self.assertIn(90, waits)
        self.assertIn(180, waits)

    def test_pending_latest_bar_recovers_on_later_round(self):
        fetch, calls = self.pending_fetch(ready_after=3)
        with patch.object(refresh, 'TICKERS', {'SPY'}), patch.object(refresh.yf, 'set_tz_cache_location'):
            frames = refresh.fetch_all(self.sessions, waits=(90, 180), sleep=lambda _: None, fetch=fetch)
        self.assertEqual(len(frames['SPY']), len(self.sessions))
        self.assertEqual(len(calls), 4)

    def test_reference_columns_twelve_one_and_risk_rank(self):
        rng = np.random.default_rng(3)
        frames = {}
        for i, ticker in enumerate(('SPY', 'QQQ', 'TLT', 'GLD')):
            close = 100 * np.exp(np.cumsum(0.0005 * i + 0.01 * rng.standard_normal(260)))
            frames[ticker] = pd.DataFrame({'time_key': pd.bdate_range('2025-01-01', periods=260),
                                           'open': close, 'high': close * 1.01, 'low': close * 0.99,
                                           'close': close, 'volume': 1e6})
        result = metrics(frames).set_index('ticker')
        spy = frames['SPY']['close']
        self.assertAlmostEqual(result.loc['SPY', 'mom12_1'], spy.iloc[-22] / spy.iloc[-253] - 1)
        self.assertEqual(sorted(result['rank_risk']), [1, 2, 3, 4])
        self.assertTrue(np.isfinite(result.select_dtypes(include='number').to_numpy()).all())
        # Too little history: 12-1 is missing rather than wrong.
        short = metrics({t: f.iloc[-200:].reset_index(drop=True) for t, f in frames.items()})
        self.assertTrue(short['mom12_1'].isna().all())

    def test_window_has_a_year_for_twelve_one(self):
        self.assertGreaterEqual(len(refresh.completed_sessions('2026-09-23T23:37:00Z')), refresh.MIN_SESSIONS)

    def test_score_history_matches_todays_score_and_is_oldest_first(self):
        rng = np.random.default_rng(5)
        sessions = pd.bdate_range('2025-01-01', periods=260)
        frames = {}
        for i, ticker in enumerate(('SPY', 'QQQ', 'TLT', 'GLD', 'XLE')):
            close = 100 * np.exp(np.cumsum(0.0004 * i + 0.01 * rng.standard_normal(260)))
            frames[ticker] = pd.DataFrame({'time_key': sessions, 'open': close, 'high': close * 1.01,
                                           'low': close * 0.99, 'close': close, 'volume': 1e6})
        history = refresh.score_history(frames, sessions, n=6)
        self.assertEqual(history['sessions'][0], str(sessions[-6].date()))
        self.assertEqual(history['asof'], str(sessions[-1].date()))
        today = metrics(frames).set_index('ticker')
        five_ago = metrics({t: f.iloc[:-5].reset_index(drop=True) for t, f in frames.items()}).set_index('ticker')
        for t in frames:
            self.assertAlmostEqual(history['tickers'][t]['score'][-1], today.at[t, 'score'], places=2)
            self.assertAlmostEqual(history['tickers'][t]['score'][0], five_ago.at[t, 'score'], places=2)
        self.assertEqual(sorted(v['rank'][-1] for v in history['tickers'].values()), [1, 2, 3, 4, 5])

    def test_market_context_regime_and_near_duplicate_peers(self):
        rng = np.random.default_rng(9)
        n = 260
        base = rng.standard_normal(n)
        series = {'SPY': 0.002 + 0.01 * base,                      # trending up
                  'QQQ': 0.002 + 0.01 * (base + 0.05 * rng.standard_normal(n)),  # near copy of SPY
                  'TLT': -0.002 + 0.01 * rng.standard_normal(n)}  # independent, trending down
        frames = {}
        for t, r in series.items():
            close = 100 * np.exp(np.cumsum(r))
            frames[t] = pd.DataFrame({'time_key': pd.bdate_range('2025-01-01', periods=n), 'open': close,
                                      'high': close, 'low': close, 'close': close, 'volume': 1e6})
        ctx = refresh.market_context(frames)
        self.assertGreater(ctx['regime']['spy_vs_sma200'], 0)
        self.assertEqual(ctx['regime']['total'], 3)
        self.assertEqual(ctx['regime']['above_sma200'], 2)
        self.assertEqual(ctx['peers']['SPY'][0][0], 'QQQ')
        self.assertGreaterEqual(ctx['peers']['SPY'][0][1], refresh.PEER_CORR)
        self.assertNotIn('TLT', ctx['peers'])

    def test_original_model_parity(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/us_model_parity.json').read_text())
        names = {'510300':'SPY'}
        names.update(zip(sorted(set(fixture['entries']) - {'510300'}), ['QQQ','DIA','IWM']))
        frames = {}
        for code, entry in fixture['entries'].items():
            frame = pd.DataFrame(entry['rows'])
            frame['time_key'] = pd.to_datetime(frame['date'])
            frames[names[code]] = frame
        actual = metrics(frames).set_index('ticker')
        for expected in fixture['expected']:
            row = actual.loc[names[expected['ticker']]]
            for key, value in expected.items():
                if key in row and isinstance(value, (int,float)) and not isinstance(value, bool):
                    self.assertAlmostEqual(row[key], value, places=10, msg=key)
            self.assertEqual(row['setup'], expected['setup'])

if __name__ == '__main__':
    unittest.main()

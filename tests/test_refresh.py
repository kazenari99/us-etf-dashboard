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

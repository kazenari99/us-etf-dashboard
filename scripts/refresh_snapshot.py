"""Refresh a complete, single-source US ETF snapshot before Pages publication."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf

from momentum import UNIVERSE, metrics

ROOT = Path(__file__).resolve().parents[1]
TICKERS = {ticker for tickers in UNIVERSE.values() for ticker in tickers.split()}


def completed_sessions(now=None):
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    if now.tzinfo is None:
        raise ValueError('A timezone-aware clock is required')
    calendar = mcal.get_calendar('NYSE')
    schedule = calendar.schedule(start_date=(now - pd.Timedelta(days=400)).date(),
                                 end_date=now.date())
    # Allow final daily bars to settle; calendar handles holidays, DST and early closes.
    closed = schedule.loc[schedule.market_close + pd.Timedelta(minutes=60) <= now]
    if closed.empty:
        raise ValueError('No completed US trading session')
    cutoff = closed.index[-1]
    sessions = closed.index[closed.index >= cutoff - pd.Timedelta(days=320)]
    return pd.DatetimeIndex(sessions).tz_localize(None)


def normalize(raw, sessions, ticker):
    if raw.empty:
        raise ValueError(f'{ticker}: empty history')
    frame = raw.rename(columns=str.lower).copy()
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_convert('America/New_York').tz_localize(None)
    frame.index = index.normalize()
    frame = frame.loc[(frame.index >= sessions[0]) & (frame.index <= sessions[-1])]
    if frame.index.has_duplicates:
        raise ValueError(f'{ticker}: duplicate sessions')
    frame = frame.sort_index()
    # Never shrink the universe, splice cached vintages, or score mismatched windows.
    if len(sessions) < 121 or not frame.index.equals(sessions):
        raise ValueError(f'{ticker}: incomplete or misaligned sessions')
    fields = ['open', 'high', 'low', 'close', 'volume']
    frame = frame[fields].astype(float)
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError(f'{ticker}: non-finite OHLCV')
    if (frame[['open', 'high', 'low', 'close']] <= 0).any().any() or (frame.volume <= 0).any():
        raise ValueError(f'{ticker}: nonpositive price or volume')
    if ((frame.high < frame[['open', 'close', 'low']].max(axis=1) - 1e-7) |
            (frame.low > frame[['open', 'close', 'high']].min(axis=1) + 1e-7)).any():
        raise ValueError(f'{ticker}: invalid OHLC bounds')
    frame.insert(0, 'time_key', frame.index)
    return frame.reset_index(drop=True)


def fetch_all(sessions):
    yf.set_tz_cache_location(str(ROOT / '.cache' / 'yfinance'))
    frames, failures = {}, {}
    for attempt in range(3):
        pending = sorted(TICKERS - frames.keys())
        if not pending:
            break
        if attempt:
            time.sleep(10 * 2 ** (attempt - 1))
        for ticker in pending:
            try:
                raw = yf.Ticker(ticker).history(
                    start=sessions[0].date().isoformat(),
                    end=(sessions[-1].date() + timedelta(days=1)).isoformat(),
                    interval='1d', auto_adjust=True, back_adjust=False,
                    actions=False, repair=False, timeout=20, raise_errors=True)
                frames[ticker] = normalize(raw, sessions, ticker)
                failures.pop(ticker, None)
                print(f'{ticker}: {len(frames[ticker])} sessions', flush=True)
            except Exception as exc:
                failures[ticker] = f'{type(exc).__name__}: {exc}'
                print(f'{ticker}: attempt {attempt + 1} failed: {exc}', flush=True)
            time.sleep(0.4)
    if failures:
        raise RuntimeError(f'Incomplete universe; keeping deployed snapshot: {failures}')
    return frames


def publish_snapshot(frames, sessions):
    if set(frames) != TICKERS:
        raise ValueError('All 71 ETFs, including SPY, are required')
    result = metrics(frames)
    if not np.isfinite(result.select_dtypes(include='number').to_numpy()).all():
        raise ValueError('Non-finite model results')
    now = datetime.now(timezone.utc)
    data = result.to_csv(index=False).encode()
    metadata = {
        'source': 'Yahoo Finance', 'transport': 'yfinance',
        'adjustment': 'Yahoo dividend and split adjusted OHLC (auto_adjust=True)',
        'asof': sessions[-1].date().isoformat(), 'generated_at': now.isoformat(),
        'count': len(result), 'expected_count': len(TICKERS),
        'sha256': hashlib.sha256(data).hexdigest(),
        'benchmark': 'SPY', 'model': 'Hermes 20/60/120 v1',
    }
    archive = ROOT / 'archive' / now.strftime('%Y-%m-%d/%H%M%S')
    archive.mkdir(parents=True)
    encoded = json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'
    (archive / 'etf_momentum_latest.csv').write_bytes(data)
    (archive / 'snapshot_meta.json').write_text(encoded)
    pd.concat(frames, names=['ticker']).to_csv(archive / 'adjusted_daily_bars.csv.gz', compression='gzip')
    # Only write public results after the entire fetch and scoring succeeds.
    (ROOT / 'dist/etf_momentum_latest.csv').write_bytes(data)
    (ROOT / 'dist/snapshot_meta.json').write_text(encoded)
    print(f'{len(result)}/{len(TICKERS)} ETFs; market date {metadata["asof"]}; Yahoo Finance')


def main():
    sessions = completed_sessions()
    print(f'Target completed session: {sessions[-1].date()}', flush=True)
    publish_snapshot(fetch_all(sessions), sessions)


if __name__ == '__main__':
    main()

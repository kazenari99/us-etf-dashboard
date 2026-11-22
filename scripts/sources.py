"""Alternative daily-bar sources. Yahoo (yfinance) stays primary.

A fallback source is used for the whole universe or not at all: one snapshot
never mixes sources, because their price adjustments can differ.
"""
from __future__ import annotations

import io
from datetime import timedelta
from urllib.request import Request, urlopen

import pandas as pd

STOOQ_URL = 'https://stooq.com/q/d/l/?s={symbol}&d1={start}&d2={end}&i=d'

SOURCES = {
    'stooq': {
        'source': 'Stooq', 'transport': 'stooq.com CSV',
        'adjustment': 'Stooq daily OHLC as published (verify with the source parity check)',
    },
}


def parse_stooq(text: str, ticker: str) -> pd.DataFrame:
    if not text.startswith('Date,'):
        # Stooq answers errors and quota messages with plain text and HTTP 200.
        raise ValueError(f'{ticker}: Stooq returned no data ({text.strip()[:60]!r})')
    frame = pd.read_csv(io.StringIO(text), parse_dates=['Date']).set_index('Date')
    if frame.empty:
        raise ValueError(f'{ticker}: Stooq returned an empty history')
    return frame[['Open', 'High', 'Low', 'Close', 'Volume']]


def fetch_stooq(ticker: str, sessions) -> pd.DataFrame:
    """Raw daily bars shaped like yfinance's history() so normalize() can validate them."""
    url = STOOQ_URL.format(symbol=f'{ticker.lower()}.us',
                           start=sessions[0].strftime('%Y%m%d'),
                           end=(sessions[-1] + timedelta(days=1)).strftime('%Y%m%d'))
    request = Request(url, headers={'User-Agent': 'us-etf-dashboard'})
    with urlopen(request, timeout=15) as response:
        return parse_stooq(response.read().decode('utf-8', 'replace'), ticker)


FETCHERS = {'stooq': fetch_stooq}

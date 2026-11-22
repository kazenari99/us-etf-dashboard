"""Report whether the live ETF snapshots lag the NYSE calendar.

Reads snapshot_meta.json from each published site and counts completed NYSE
sessions after its `asof`. A lag of one session is normal (the morning run may
still be pending); STALE_SESSIONS or more is stale.

Writes `stale=true|false` to GITHUB_OUTPUT and a markdown report to the path in
FRESHNESS_REPORT (default freshness.md).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen

import pandas as pd

from refresh_snapshot import completed_sessions

SITES = {
    'Cloudflare (orbit-us)': 'https://orbit-us.pages.dev/snapshot_meta.json',
    'GitHub Pages': 'https://kazenari99.github.io/us-etf-dashboard/snapshot_meta.json',
}
STALE_SESSIONS = 2
# Third-party candidate list: allow an extra session before alerting.
STOCKS_URL = 'https://orbit-us.pages.dev/stocks.json'
STALE_STOCK_SESSIONS = 3


def lag(asof: str, sessions: pd.DatetimeIndex) -> int:
    """Completed sessions strictly after `asof`."""
    return int((sessions > pd.Timestamp(asof)).sum())


def fetch_asof(url: str) -> str:
    request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'us-etf-dashboard-freshness'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)['asof']


def evaluate(results: dict[str, str | None], sessions: pd.DatetimeIndex,
             stocks: tuple[str | None, str] | None = None) -> tuple[bool, list[str]]:
    """`stocks` = (session_date, fetch_status) of the published stock list, if checked."""
    latest = sessions[-1].date()
    lines = [f'Latest completed NYSE session: **{latest}** (stale at {STALE_SESSIONS}+ sessions behind)', '',
             '| Site | Published session | Sessions behind |', '|---|---|---:|']
    stale = False
    for site, asof in results.items():
        if asof is None:
            stale = True
            lines.append(f'| {site} | unreachable | — |')
            continue
        behind = lag(asof, sessions)
        stale |= behind >= STALE_SESSIONS
        lines.append(f'| {site} | {asof} | {behind} |')
    if stocks is not None:
        session, status = stocks
        if session is None:
            stale = True
            lines.append('| Stock candidates (orbit-us) | unreachable | — |')
        else:
            behind = lag(session, sessions)
            stale |= behind >= STALE_STOCK_SESSIONS
            lines.append(f'| Stock candidates (orbit-us), last fetch {status} | {session} | {behind} |')
        lines.append('')
        lines.append(f'Stock candidates come from a third-party list; stale at {STALE_STOCK_SESSIONS}+ sessions behind.')
    return stale, lines


def main():
    sessions = completed_sessions()
    results = {}
    for site, url in SITES.items():
        try:
            results[site] = fetch_asof(url)
        except Exception as exc:  # noqa: BLE001 - report any fetch failure as unreachable
            print(f'{site}: {type(exc).__name__}: {exc}')
            results[site] = None
    try:
        request = Request(STOCKS_URL, headers={'Cache-Control': 'no-cache', 'User-Agent': 'us-etf-dashboard-freshness'})
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        stocks = (payload.get('session_date'), payload.get('fetch_status', 'unknown'))
    except Exception as exc:  # noqa: BLE001
        print(f'Stocks: {type(exc).__name__}: {exc}')
        stocks = (None, 'unreachable')
    stale, lines = evaluate(results, sessions, stocks)
    lines += ['', f'Checked {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.']
    report = '\n'.join(lines) + '\n'
    print(report)
    with open(os.environ.get('FRESHNESS_REPORT', 'freshness.md'), 'w') as out:
        out.write(report)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f'stale={str(stale).lower()}\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write(report)


if __name__ == '__main__':
    main()

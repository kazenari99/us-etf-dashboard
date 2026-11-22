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


def lag(asof: str, sessions: pd.DatetimeIndex) -> int:
    """Completed sessions strictly after `asof`."""
    return int((sessions > pd.Timestamp(asof)).sum())


def fetch_asof(url: str) -> str:
    request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'us-etf-dashboard-freshness'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)['asof']


def evaluate(results: dict[str, str | None], sessions: pd.DatetimeIndex) -> tuple[bool, list[str]]:
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
    stale, lines = evaluate(results, sessions)
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

"""Validate the ETF snapshot in dist/ before it is published.

Explicit checks (not `assert`, which `python -O` strips). Exits non-zero with the
first problem found.
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

from momentum import UNIVERSE

ROOT = Path(__file__).resolve().parents[1]
FINITE_FIELDS = ('close', 'r20', 'r60', 'r120', 'score', 'atr14')


class SnapshotError(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise SnapshotError(message)


def validate(dist: Path) -> str:
    """Return a one-line summary; raise SnapshotError on any problem."""
    csv_path = dist / 'etf_momentum_latest.csv'
    rows = list(csv.DictReader(csv_path.open()))
    check(rows, 'Empty snapshot')
    tickers = {r['ticker'] for r in rows}
    check(len(tickers) == len(rows), 'Duplicate tickers')
    check(len({r['date'] for r in rows}) == 1, 'Mixed market dates')
    for row in rows:
        for key in FINITE_FIELDS:
            try:
                ok = math.isfinite(float(row[key]))
            except (KeyError, ValueError):
                ok = False
            check(ok, f'{row["ticker"]} invalid {key}')
    check('SPY' in tickers, 'Benchmark missing')

    expected = {t for group in UNIVERSE.values() for t in group.split()}
    meta = json.loads((dist / 'snapshot_meta.json').read_text())
    warning = ''
    if 'universe' in meta and set(meta['universe']) == expected:
        check(tickers == expected, 'Incomplete universe')
    else:
        # Published before the current universe: must still match its own recorded universe.
        check(tickers == set(meta.get('universe', tickers)), 'Incomplete universe')
        warning = (f'::warning title=Previous ETF universe::Snapshot {meta["asof"]} has {len(rows)} ETFs '
                   f'from an earlier universe; the next ETF refresh publishes all {len(expected)}.')
    check(meta.get('asof') == rows[0]['date'], 'Metadata date mismatch')
    check(meta.get('count') == meta.get('expected_count') == len(rows), 'Metadata count mismatch')
    check(meta.get('sha256') == hashlib.sha256(csv_path.read_bytes()).hexdigest(), 'Checksum mismatch')
    if warning:
        print(warning)
    return f'{len(rows)} ETFs / {rows[0]["date"]} / snapshot validated'


def main():
    try:
        print(validate(ROOT / 'dist'))
    except (SnapshotError, OSError, json.JSONDecodeError) as exc:
        print(f'::error title=Snapshot validation failed::{exc}')
        sys.exit(1)


if __name__ == '__main__':
    main()

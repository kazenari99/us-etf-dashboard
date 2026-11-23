"""Out-of-sample check of the published rankings, from the data branch.

Each daily snapshot (etf/<asof>.csv) stores every ETF's score and close as
published that day. For each snapshot, the published top N is followed to a
later snapshot H sessions ahead using those stored closes, and compared with
SPY and the equal-weight universe. Nothing is re-fetched or re-scored, so this
measures what the dashboard actually showed.

Usage: live_report.py HISTORY_DIR [OUT.md]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TOP = 10
HORIZONS = (5, 20)
MIN_PERIODS = 8          # below this, say "not enough data yet" instead of numbers


def load(history: Path) -> dict[str, pd.DataFrame]:
    snaps = {}
    for path in sorted((history / 'etf').glob('????-??-??.csv')):
        frame = pd.read_csv(path)
        if {'ticker', 'score', 'close'} <= set(frame.columns):
            snaps[path.stem] = frame.set_index('ticker')
    return snaps


def forward(snaps: dict[str, pd.DataFrame], horizon: int, step: int) -> pd.DataFrame:
    """One row per start snapshot (every `step`): top-N, SPY, equal-weight returns, rank IC."""
    dates = sorted(snaps)
    rows = []
    for i in range(0, len(dates) - horizon, step):
        start, end = snaps[dates[i]], snaps[dates[i + horizon]]
        common = start.index.intersection(end.index)
        ret = end.loc[common, 'close'] / start.loc[common, 'close'] - 1
        score = start.loc[common, 'score']
        top = score.nlargest(TOP).index
        rows.append({'start': dates[i], 'end': dates[i + horizon], 'top': ret[top].mean(),
                     'spy': ret.get('SPY', np.nan), 'ew': ret.mean(),
                     'ic': score.rank().corr(ret.rank())})
    return pd.DataFrame(rows)


def report(snaps: dict[str, pd.DataFrame]) -> str:
    dates = sorted(snaps)
    lines = ['# Live tracking of published rankings', '',
             f'Snapshots on the data branch: **{len(dates)}**'
             + (f' ({dates[0]} → {dates[-1]})' if dates else '') + '.',
             f'Each published top {TOP} by score is followed to the snapshot H sessions later using the closes '
             'stored in the snapshots (price return as published; no re-fetch, no re-scoring).', '']
    for h in HORIZONS:
        lines += [f'## {h}-session horizon', '']
        nonoverlap = forward(snaps, h, step=h)
        if len(nonoverlap) < MIN_PERIODS:
            lines += [f'Not enough data yet: {len(nonoverlap)} non-overlapping periods, need {MIN_PERIODS} '
                      f'(about {MIN_PERIODS * h + h} snapshots).', '']
            continue
        allstarts = forward(snaps, h, step=1)
        excess = nonoverlap['top'] - nonoverlap['spy']
        cum = lambda s: float((1 + s).prod() - 1)  # noqa: E731
        lines += ['| | Top 10 | SPY | Equal-weight |', '|---|---:|---:|---:|',
                  f'| Average return per period | {nonoverlap.top.mean():+.2%} | {nonoverlap.spy.mean():+.2%} | '
                  f'{nonoverlap.ew.mean():+.2%} |',
                  f'| Compounded over {len(nonoverlap)} periods | {cum(nonoverlap.top):+.1%} | '
                  f'{cum(nonoverlap.spy):+.1%} | {cum(nonoverlap.ew):+.1%} |', '',
                  f'- Top 10 beat SPY in **{(excess > 0).mean():.0%}** of {len(nonoverlap)} periods; '
                  f'average excess {excess.mean():+.2%} (t = {excess.mean() / (excess.std(ddof=1) / np.sqrt(len(excess))):+.2f}).',
                  f'- Mean rank IC (score vs forward return, all {len(allstarts)} start days): '
                  f'**{allstarts.ic.mean():.3f}**.', '',
                  'Last periods:', '', '| Start | End | Top 10 | SPY |', '|---|---|---:|---:|']
        for _, r in nonoverlap.tail(6).iloc[::-1].iterrows():
            lines.append(f"| {r.start} | {r.end} | {r.top:+.2%} | {r.spy:+.2%} |")
        lines.append('')
    lines += ['Past results do not guarantee future returns. Not investment advice.']
    return '\n'.join(lines) + '\n'


def main():
    history = Path(sys.argv[1])
    text = report(load(history))
    print(text)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(text)


if __name__ == '__main__':
    main()

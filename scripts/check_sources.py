"""Compare a fallback source with Yahoo before enabling it (FALLBACK_SOURCE).

Fetches every ETF from both, validates both with the production normalize(),
then reports price and return differences per ETF and how much the score ranking
would change. Writes a markdown report to GITHUB_STEP_SUMMARY and stdout.
"""
from __future__ import annotations

import os
import sys
import time


from momentum import metrics
from refresh_snapshot import TICKERS, completed_sessions, fetch_history, normalize
from sources import FETCHERS

# Enable the fallback only if all of these hold.
MAX_R120_DIFF = 0.01     # 1 percentage point
MIN_RANK_CORR = 0.98
MIN_TOP10_OVERLAP = 8
PROBE = ('SPY', 'QQQ', 'TLT')


def compare(yahoo: dict, other: dict) -> tuple[list[str], bool]:
    common = sorted(set(yahoo) & set(other))
    rows, worst = [], 0.0
    for t in common:
        y, o = yahoo[t], other[t]
        close = o['close'].iloc[-1] / y['close'].iloc[-1] - 1
        diffs = [o['close'].iloc[-1] / o['close'].iloc[-1 - n] - (y['close'].iloc[-1] / y['close'].iloc[-1 - n])
                 for n in (20, 60, 120)]
        worst = max(worst, abs(diffs[2]))
        rows.append((abs(diffs[2]), f'| {t} | {close:+.2%} | {diffs[0]:+.2%} | {diffs[1]:+.2%} | {diffs[2]:+.2%} |'))
    lines = ['| ETF | Close diff | r20 diff | r60 diff | r120 diff |', '|---|---:|---:|---:|---:|']
    lines += [r for _, r in sorted(rows, reverse=True)[:15]]
    ok = bool(common) and len(common) == len(TICKERS) and worst < MAX_R120_DIFF
    corr = overlap = float('nan')
    if 'SPY' in common and len(common) >= 10:
        a = metrics({t: yahoo[t] for t in common}).set_index('ticker')['score']
        b = metrics({t: other[t] for t in common}).set_index('ticker')['score'].reindex(a.index)
        corr = float(a.rank().corr(b.rank()))
        overlap = len(set(a.nlargest(10).index) & set(b.nlargest(10).index))
        ok = ok and corr >= MIN_RANK_CORR and overlap >= MIN_TOP10_OVERLAP
    summary = [f'Compared ETFs: **{len(common)}/{len(TICKERS)}** · largest |r120 diff| **{worst:.2%}** '
               f'(limit {MAX_R120_DIFF:.0%}) · score rank correlation **{corr:.3f}** (min {MIN_RANK_CORR}) · '
               f'top-10 overlap **{overlap}/10** (min {MIN_TOP10_OVERLAP})', '',
               f'Verdict: **{"OK to enable" if ok else "do not enable"}**', '', '15 largest r120 differences:', '']
    return summary + lines, ok


def main():
    name = (sys.argv[1] if len(sys.argv) > 1 else 'stooq').lower()
    fetch_other = FETCHERS[name]
    sessions = completed_sessions()
    yahoo, other, errors = {}, {}, []
    # Probe first: if the backup source does not answer for a few liquid ETFs,
    # stop now with a clear verdict instead of waiting out every timeout.
    probe_errors = []
    for t in PROBE:
        started = time.monotonic()
        try:
            normalize(fetch_other(t, sessions), sessions, t)
            print(f'probe {name} {t}: ok in {time.monotonic() - started:.1f}s', flush=True)
        except Exception as exc:  # noqa: BLE001
            probe_errors.append(f'- {name} {t}: {type(exc).__name__}: {str(exc)[:160]}')
            print(f'probe {name} {t}: failed in {time.monotonic() - started:.1f}s: {exc}', flush=True)
    if len(probe_errors) == len(PROBE):
        report = '\n'.join([f'# Source parity: {name} vs Yahoo', '',
                             f'Verdict: **do not enable** — {name} did not return valid data for any probe ETF '
                             f'({", ".join(PROBE)}) from this runner.', '', *probe_errors]) + '\n'
        print(report)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
                out.write(report)
        print(f'::notice title=Source parity::{name} is not reachable or returns no data from GitHub Actions')
        return
    for i, t in enumerate(sorted(TICKERS), 1):
        if i % 10 == 0:
            print(f'{i}/{len(TICKERS)} ETFs compared', flush=True)
        for label, fetch, store in (('Yahoo', fetch_history, yahoo), (name, fetch_other, other)):
            try:
                store[t] = normalize(fetch(t, sessions), sessions, t)
            except Exception as exc:  # noqa: BLE001 - every failure is part of the report
                errors.append(f'- {label} {t}: {type(exc).__name__}: {str(exc)[:120]}')
            time.sleep(0.3)
    lines, ok = compare(yahoo, other)
    report = '\n'.join([f'# Source parity: {name} vs Yahoo', '', f'Session: {sessions[-1].date()}', '', *lines,
                        '', f'Fetch errors ({len(errors)}):', '', *(errors[:40] or ['- none'])]) + '\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write(report)
    if not ok:
        print(f'::notice title=Source parity::{name} should not be enabled as FALLBACK_SOURCE yet')


if __name__ == '__main__':
    main()

"""Walk-forward backtest of the ETF momentum score and candidate variants.

Replays the production `metrics()` on each weekly rebalance date using only data
available at that close, then holds the top-N ETFs until the next rebalance.

Usage: python scripts/backtest.py [--start 2018-01-01] [--top 5 10] [--out backtest]

Known biases (stated in the report too): the universe is today's list, chosen
with hindsight; ETFs enter only once they have enough history; Yahoo adjusted
prices are revised retroactively for dividends.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from momentum import UNIVERSE, metrics

ROOT = Path(__file__).resolve().parents[1]
TICKERS = sorted({t for tickers in UNIVERSE.values() for t in tickers.split()})
GROUP = {t: g for g, tickers in UNIVERSE.items() for t in tickers.split()}
MIN_BARS = 130          # metrics() needs 121 closes plus the ATR/EMA warm-up
WINDOW = 260            # bars passed to metrics() per date; enough for every rolling field
COST = 0.0005           # 5 bp per unit of one-way turnover
LAG = 2                 # signal at close t, trade at close t+1, earn returns from t+2
HORIZONS = (5, 20)      # forward sessions for rank-IC and quintile spreads
WEIGHTS = ((20, 0.30), (60, 0.40), (120, 0.30))


def download(start: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    yf.set_tz_cache_location(str(ROOT / '.cache' / 'yfinance'))
    raw = yf.download(TICKERS, start=start, auto_adjust=True, group_by='ticker',
                      actions=False, progress=False, threads=True)
    frames = {}
    for ticker in TICKERS:
        try:
            frame = raw[ticker].rename(columns=str.lower)[['open', 'high', 'low', 'close', 'volume']]
        except KeyError:
            continue
        frame = frame.dropna()
        frame = frame[(frame[['open', 'high', 'low', 'close']] > 0).all(axis=1) & (frame.volume > 0)]
        if len(frame) >= MIN_BARS:
            frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
            frames[ticker] = frame
    if 'SPY' not in frames:
        raise SystemExit('SPY history unavailable')
    missing = sorted(set(TICKERS) - set(frames))
    print(f'Downloaded {len(frames)}/{len(TICKERS)} ETFs' + (f'; missing {missing}' if missing else ''))
    return frames


def rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last session of each calendar week."""
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period('W')).max().to_numpy())


def risk_adjusted(close: pd.DataFrame) -> dict[int, pd.DataFrame]:
    daily = close.pct_change(fill_method=None)
    return {n: (close / close.shift(n) - 1) / (daily.rolling(n).std() * np.sqrt(n)) for n, _ in WEIGHTS}


def score(table: pd.DataFrame, columns: dict[int, str], by_group: bool = False) -> pd.Series:
    """Production scoring with a different input to the percentile ranks."""
    total = pd.Series(0.0, index=table.index)
    for n, weight in WEIGHTS:
        values = table[columns[n]]
        ranks = values.groupby(table['group']).rank(pct=True) if by_group else values.rank(pct=True)
        total += weight * ranks
    total *= 100
    total += np.where(table['trend_aligned'], 5, 0)
    total += np.where(table['rs60'] > 0, 3, 0)
    total -= np.where(table['dist_ema_atr'] > 2.5, 8, 0)
    return total


def signals(frames: dict[str, pd.DataFrame], dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.DataFrame({t: f['close'] for t, f in frames.items()}).sort_index()
    ra = risk_adjusted(close)
    spy_sma200 = close['SPY'].rolling(200).mean()
    rows = []
    for i, date in enumerate(dates):
        window = {}
        for ticker, frame in frames.items():
            upto = frame.loc[:date]
            if len(upto) < MIN_BARS or upto.index[-1] != date:
                continue
            part = upto.iloc[-WINDOW:].copy()
            part.insert(0, 'time_key', part.index)
            window[ticker] = part.reset_index(drop=True)
        if 'SPY' not in window or len(window) < 10:
            continue
        table = metrics(window).set_index('ticker')
        for n, _ in WEIGHTS:
            table[f'ra{n}'] = ra[n].loc[date].reindex(table.index)
        table = table.dropna(subset=[f'ra{n}' for n, _ in WEIGHTS])
        table['score_risk'] = score(table, {n: f'ra{n}' for n, _ in WEIGHTS})
        table['score_group'] = score(table, {n: f'r{n}' for n, _ in WEIGHTS}, by_group=True)
        table['risk_off'] = bool(close['SPY'].loc[date] < spy_sma200.loc[date])
        table['date'] = date
        rows.append(table.reset_index()[['date', 'ticker', 'group', 'score', 'score_risk',
                                         'score_group', 'setup', 'risk_off']])
        if i % 50 == 0:
            print(f'{date.date()}: {len(table)} ETFs', flush=True)
    return pd.concat(rows, ignore_index=True)


def ema_trend(close: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    """True while EMA(fast) is above EMA(slow): bought on the up-cross, sold on the down-cross."""
    fast_ema = close.ewm(span=fast, adjust=False, min_periods=slow).mean()
    slow_ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    return fast_ema > slow_ema


def portfolio(weights: pd.DataFrame, returns: pd.DataFrame, mask: pd.DataFrame | None = None) -> pd.Series:
    """Daily net returns for weights decided on rebalance dates (rows) with LAG and costs.

    `mask` (daily, by ticker) zeroes a position on days it is False; that slot sits in cash.
    """
    daily = weights.reindex(returns.index).ffill().fillna(0.0)
    if mask is not None:
        daily = daily * mask.reindex(index=daily.index, columns=daily.columns).fillna(False).astype(float)
    held = daily.shift(LAG).fillna(0.0)
    gross = (held * returns.fillna(0.0)).sum(axis=1)
    turnover = held.diff().abs().sum(axis=1).fillna(held.abs().sum(axis=1))
    return gross - COST * turnover


def top_weights(sig: pd.DataFrame, column: str, n: int, *, momentum_only=False, regime=False,
                cash='BIL') -> pd.DataFrame:
    out = {}
    for date, day in sig.groupby('date'):
        if regime and day['risk_off'].iloc[0]:
            out[date] = {cash: 1.0} if cash in set(day['ticker']) else {}
            continue
        pool = day[day['setup'] == 'Momentum'] if momentum_only else day
        picks = pool.nlargest(n, column)['ticker']
        out[date] = {t: 1.0 / n for t in picks}  # unfilled slots stay in cash
    return pd.DataFrame.from_dict(out, orient='index').fillna(0.0).sort_index()


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    r = r.loc[r.ne(0).idxmax():] if r.ne(0).any() else r
    equity = (1 + r).cumprod()
    years = len(r) / 252
    return {
        'CAGR': equity.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan,
        'Vol': r.std() * np.sqrt(252),
        'Sharpe': r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
        'MaxDD': (equity / equity.cummax() - 1).min(),
        'Total': equity.iloc[-1] - 1,
    }


def rank_ic(sig: pd.DataFrame, close: pd.DataFrame, column: str, horizon: int) -> tuple[float, float]:
    """Mean Spearman IC and top-minus-bottom quintile forward return, both with LAG."""
    entry = close.shift(-(LAG - 1))
    forward = close.shift(-(LAG - 1 + horizon)) / entry - 1
    ics, spreads = [], []
    for date, day in sig.groupby('date'):
        if date not in forward.index:
            continue
        fwd = forward.loc[date].reindex(day['ticker']).to_numpy()
        ok = np.isfinite(fwd)
        if ok.sum() < 10:
            continue
        s = day[column].to_numpy()[ok]
        f = fwd[ok]
        ics.append(pd.Series(s).rank().corr(pd.Series(f).rank()))
        q = pd.qcut(pd.Series(s).rank(method='first'), 5, labels=False)
        spreads.append(f[q.to_numpy() == 4].mean() - f[q.to_numpy() == 0].mean())
    return float(np.nanmean(ics)), float(np.nanmean(spreads))


SKIP = 21               # skip the most recent month in long-lookback momentum
LONG_BARS = 253         # 12 months of closes plus one


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last session of each calendar month."""
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period('M')).max().to_numpy())


def long_momentum(close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Classic cross-asset momentum scores, all skipping the most recent month."""
    m6 = close.shift(SKIP) / close.shift(126) - 1
    m12 = close.shift(SKIP) / close.shift(252) - 1
    vol = close.pct_change(fill_method=None).rolling(252).std() * np.sqrt(252)
    enough = close.notna().rolling(LONG_BARS).sum() >= LONG_BARS
    out = {'12-1': m12, '6-1': m6, 'blend': (m6.rank(axis=1, pct=True) + m12.rank(axis=1, pct=True)) / 2,
           '12-1 / vol': m12 / vol}
    return {k: v.where(enough) for k, v in out.items()}


def pick_top(scores: pd.DataFrame, dates, n: int, absolute: pd.DataFrame | None = None,
             cash: str = 'BIL') -> pd.DataFrame:
    """Equal-weight top-n per date; with `absolute`, a pick whose 12-1 return trails
    the cash ETF's 12-1 return is swapped for the cash ETF."""
    out = {}
    for date in dates:
        row = scores.loc[date].dropna()
        if len(row) < n:
            continue
        weights = {}
        for ticker in row.nlargest(n).index:
            fails = absolute is not None and cash in absolute.columns and \
                absolute.at[date, ticker] <= absolute.at[date, cash]
            target = cash if fails else ticker
            weights[target] = weights.get(target, 0.0) + 1.0 / n
        out[date] = weights
    return pd.DataFrame.from_dict(out, orient='index').fillna(0.0).sort_index()


def monthly_section(close: pd.DataFrame, sig: pd.DataFrame, tops) -> list[str]:
    returns = close.pct_change(fill_method=None)
    mom = long_momentum(close)
    dates = [d for d in month_ends(close['SPY'].dropna().index) if mom['12-1'].loc[d].notna().sum() >= 20]
    if len(dates) < 12:
        return ['', '## Monthly rebalance, 6–12 month momentum', '', 'Not enough history; start earlier.']
    first = dates[0]
    r = returns.loc[first:]
    weekly_dates = set(sig['date'])
    month_sig = sig[sig['date'].isin([max((w for w in weekly_dates if w.to_period('M') == d.to_period('M')),
                                          default=None) for d in dates])]
    strategies = {'SPY buy & hold': r['SPY'].fillna(0.0)}
    for n in tops:
        strategies[f'Current score, top {n}, monthly'] = portfolio(top_weights(month_sig, 'score', n), r)
        for key in ('12-1', '6-1', 'blend', '12-1 / vol'):
            strategies[f'{key} momentum, top {n}'] = portfolio(pick_top(mom[key], dates, n), r)
        strategies[f'12-1 momentum, top {n}, BIL if not beating BIL'] = portfolio(
            pick_top(mom['12-1'], dates, n, absolute=mom['12-1']), r)
        strategies[f'blend momentum, top {n}, BIL if not beating BIL'] = portfolio(
            pick_top(mom['blend'], dates, n, absolute=mom['12-1']), r)
    table = pd.DataFrame({k: stats(v) for k, v in strategies.items()}).T
    lines = ['', '## Monthly rebalance, 6–12 month momentum', '',
             f'Window: {first.date()} – {r.index[-1].date()}, {len(dates)} month-end rebalances. '
             'Momentum = return from 12 (or 6) months ago to 1 month ago; blend = average of the two ranks; '
             '"BIL if not beating BIL" swaps a pick for BIL when its 12-1 return is not above BIL\'s.', '',
             '| Strategy | CAGR | Vol | Sharpe | Max DD | Total |', '|---|---:|---:|---:|---:|---:|']
    for name, row in table.iterrows():
        lines.append(f'| {name} | {row.CAGR:.1%} | {row.Vol:.1%} | {row.Sharpe:.2f} | {row.MaxDD:.1%} | {row.Total:.0%} |')
    lines += ['', '| Signal | Rank IC 21d | Q5–Q1 21d |', '|---|---:|---:|']
    for key in ('12-1', '6-1', 'blend', '12-1 / vol'):
        long = mom[key].loc[dates].stack().rename('score').reset_index()
        long.columns = ['date', 'ticker', 'score']
        ic, spread = rank_ic(long, close, 'score', 21)
        lines.append(f'| {key} | {ic:.3f} | {spread:.2%} |')
    return lines


def report(frames, sig, tops, start) -> str:
    close = pd.DataFrame({t: f['close'] for t, f in frames.items()}).sort_index()
    returns = close.pct_change(fill_method=None)
    first = sig['date'].min()
    returns = returns.loc[first:]
    universe_w = sig.assign(w=1.0).pivot_table(index='date', columns='ticker', values='w').fillna(0.0)
    universe_w = universe_w.div(universe_w.sum(axis=1), axis=0)
    trend = ema_trend(close).loc[first:]
    spy_w = pd.DataFrame({'SPY': [1.0]}, index=[first])
    strategies = {'SPY buy & hold': returns['SPY'].fillna(0.0),
                  'SPY, EMA5 > EMA20 only': portfolio(spy_w, returns, mask=trend),
                  'Equal-weight universe (weekly)': portfolio(universe_w, returns)}
    for n in tops:
        strategies[f'Current score, top {n}'] = portfolio(top_weights(sig, 'score', n), returns)
        strategies[f'Current score, top {n}, Momentum setup only'] = portfolio(
            top_weights(sig, 'score', n, momentum_only=True), returns)
        strategies[f'Risk-adjusted ranks, top {n}'] = portfolio(top_weights(sig, 'score_risk', n), returns)
        strategies[f'Within-group ranks, top {n}'] = portfolio(top_weights(sig, 'score_group', n), returns)
        strategies[f'Current score, top {n}, BIL when SPY < 200d'] = portfolio(
            top_weights(sig, 'score', n, regime=True), returns)
        strategies[f'Current score, top {n}, EMA5 > EMA20'] = portfolio(
            top_weights(sig, 'score', n), returns, mask=trend)
        strategies[f'Risk-adjusted ranks, top {n}, EMA5 > EMA20'] = portfolio(
            top_weights(sig, 'score_risk', n), returns, mask=trend)
    table = pd.DataFrame({k: stats(v) for k, v in strategies.items()}).T
    yearly = pd.DataFrame({k: (1 + v).groupby(v.index.year).prod() - 1 for k, v in strategies.items()}).T

    lines = ['# ETF momentum backtest', '',
             f'Window: {first.date()} – {returns.index[-1].date()} (data from {start}), '
             f'{sig["date"].nunique()} weekly rebalances, {sig["ticker"].nunique()} ETFs, '
             f'trade at next close, {COST * 1e4:.0f} bp per one-way turnover.', '',
             '## Strategies', '', '| Strategy | CAGR | Vol | Sharpe | Max DD | Total |', '|---|---:|---:|---:|---:|---:|']
    for name, row in table.iterrows():
        lines.append(f'| {name} | {row.CAGR:.1%} | {row.Vol:.1%} | {row.Sharpe:.2f} | {row.MaxDD:.1%} | {row.Total:.0%} |')
    lines += ['', '## Does a higher score predict higher returns?', '',
              'Rank IC = average Spearman correlation between score and forward return across ETFs '
              '(0 = no signal; 0.05+ is useful for weekly data). Q5–Q1 = top-fifth minus bottom-fifth forward return.', '',
              '| Score | ' + ' | '.join(f'IC {h}d | Q5–Q1 {h}d' for h in HORIZONS) + ' |',
              '|---|' + '---:|---:|' * len(HORIZONS)]
    for col, label in (('score', 'Current'), ('score_risk', 'Risk-adjusted'), ('score_group', 'Within-group')):
        cells = []
        for h in HORIZONS:
            ic, spread = rank_ic(sig, close, col, h)
            cells += [f'{ic:.3f}', f'{spread:.2%}']
        lines.append(f'| {label} | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Calendar-year returns', '', '| Strategy | ' + ' | '.join(str(y) for y in yearly.columns) + ' |',
              '|---|' + '---:|' * len(yearly.columns)]
    for name, row in yearly.iterrows():
        lines.append(f'| {name} | ' + ' | '.join(f'{v:.0%}' for v in row) + ' |')
    lines += monthly_section(close, sig, tops)
    lines += ['', '## Caveats', '',
              '- Universe is today\'s 80 ETFs, chosen with hindsight (survivorship/selection bias).',
              '- ETFs join only after ~130 sessions of history (e.g. IBIT from mid-2024).',
              '- Yahoo dividend-adjusted prices; no taxes, slippage beyond the flat cost, or borrow.',
              '- Past results do not guarantee future returns. Not investment advice.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2018-01-01')
    parser.add_argument('--top', type=int, nargs='+', default=[5, 10])
    parser.add_argument('--out', type=Path, default=ROOT / 'backtest')
    args = parser.parse_args()
    frames = download(args.start)
    spy = frames['SPY'].index
    dates = rebalance_dates(spy[spy >= spy[MIN_BARS]])
    sig = signals(frames, dates)
    args.out.mkdir(parents=True, exist_ok=True)
    sig.to_csv(args.out / 'signals.csv.gz', index=False, compression='gzip')
    text = report(frames, sig, args.top, args.start)
    (args.out / 'report.md').write_text(text)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as out:
            out.write(text)
    print(text)


if __name__ == '__main__':
    main()

import csv
import math
import hashlib
import json
from pathlib import Path
from momentum import UNIVERSE
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'dist/etf_momentum_latest.csv').open()))
assert rows,'Empty snapshot'
assert len({r['ticker'] for r in rows})==len(rows),'Duplicate tickers'
assert len({r['date'] for r in rows})==1,'Mixed market dates'
for row in rows:
    for k in ('close','r20','r60','r120','score','atr14'):
        assert math.isfinite(float(row[k])),f'{row["ticker"]} invalid {k}'
assert any(r['ticker']=='SPY' for r in rows),'Benchmark missing'
expected = {ticker for tickers in UNIVERSE.values() for ticker in tickers.split()}
meta = json.loads((root/'dist/snapshot_meta.json').read_text())
tickers = {r['ticker'] for r in rows}
if 'universe' in meta and set(meta['universe']) == expected:
    assert tickers == expected, 'Incomplete universe'
else:
    # Published before the current universe: must still match its own recorded universe.
    assert tickers == set(meta.get('universe', tickers)), 'Incomplete universe'
    print(f'::warning title=Previous ETF universe::Snapshot {meta["asof"]} has {len(rows)} ETFs '
          f'from an earlier universe; the next ETF refresh publishes all {len(expected)}.')
assert meta['asof'] == rows[0]['date'], 'Metadata date mismatch'
assert meta['count'] == meta['expected_count'] == len(rows), 'Metadata count mismatch'
assert meta['sha256'] == hashlib.sha256((root/'dist/etf_momentum_latest.csv').read_bytes()).hexdigest(), 'Checksum mismatch'
print(f'{len(rows)} ETFs / {rows[0]["date"]} / snapshot validated')

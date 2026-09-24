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
assert {r['ticker'] for r in rows} == expected, 'Incomplete universe'
meta = json.loads((root/'dist/snapshot_meta.json').read_text())
assert meta['asof'] == rows[0]['date'], 'Metadata date mismatch'
assert meta['count'] == meta['expected_count'] == len(rows), 'Metadata count mismatch'
assert meta['sha256'] == hashlib.sha256((root/'dist/etf_momentum_latest.csv').read_bytes()).hexdigest(), 'Checksum mismatch'
print(f'{len(rows)} ETFs / {rows[0]["date"]} / snapshot validated')

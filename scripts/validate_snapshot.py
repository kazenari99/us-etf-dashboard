import csv
import math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'dist/etf_momentum_latest.csv').open()))
assert rows,'Empty snapshot'
assert len({r['ticker'] for r in rows})==len(rows),'Duplicate tickers'
assert len({r['date'] for r in rows})==1,'Mixed market dates'
for row in rows:
    for k in ('close','r20','r60','r120','score','atr14'):
        assert math.isfinite(float(row[k])),f'{row["ticker"]} invalid {k}'
assert any(r['ticker']=='SPY' for r in rows),'Benchmark missing'
print(f'{len(rows)} ETFs / {rows[0]["date"]} / snapshot validated')

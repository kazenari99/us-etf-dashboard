"""Build two throwaway sites for the browser smoke test.

current/: dist/ plus a synthetic 80-ETF snapshot with score history, regime and a
          correlated cluster (exercises every current feature).
legacy/:  dist/ exactly as committed (older snapshot, no history file) to prove
          the page still renders data published before newer features existed.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import refresh_snapshot as rs  # noqa: E402
from momentum import metrics  # noqa: E402


def main(out: Path):
    for name in ('current', 'legacy'):
        shutil.rmtree(out / name, ignore_errors=True)
        shutil.copytree(ROOT / 'dist', out / name)
    (out / 'legacy' / 'etf_history.json').unlink(missing_ok=True)

    rng = np.random.default_rng(11)
    sessions = pd.bdate_range('2025-10-20', periods=275)
    cluster, common = {'XLK', 'SMH', 'IGV', 'QQQ'}, rng.standard_normal(275)
    frames = {}
    for i, t in enumerate(sorted(rs.TICKERS)):
        noise = common if t in cluster else rng.standard_normal(275)
        drift = 0.0012 if t in cluster else 0.0003 * (i % 9 - 4)
        close = 100 * np.exp(np.cumsum(drift + 0.01 * (noise + 0.15 * rng.standard_normal(275))))
        frames[t] = pd.DataFrame({'time_key': sessions, 'open': close, 'high': close * 1.01,
                                  'low': close * 0.99, 'close': close, 'volume': 1e6 * (1 + i)})
    result = metrics(frames)
    data = result.to_csv(index=False).encode()
    history = {**rs.score_history(frames, sessions), **rs.market_context(frames)}
    site = out / 'current'
    (site / 'etf_momentum_latest.csv').write_bytes(data)
    (site / 'etf_history.json').write_text(json.dumps(history))
    meta = json.loads((site / 'snapshot_meta.json').read_text())
    meta.update(source='Yahoo Finance', asof=history['asof'], count=len(result), expected_count=len(result),
                universe=sorted(rs.TICKERS), sha256=hashlib.sha256(data).hexdigest(),
                generated_at=pd.Timestamp.now(tz='UTC').isoformat())
    (site / 'snapshot_meta.json').write_text(json.dumps(meta))
    print(f'Built {out}/current ({len(result)} ETFs) and {out}/legacy')


if __name__ == '__main__':
    main(Path(sys.argv[1]))

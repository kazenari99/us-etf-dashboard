"""Copy an existing local US snapshot; never requests OpenD data."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import csv
import hashlib
import json
from datetime import datetime, timezone
p=argparse.ArgumentParser();p.add_argument('source',type=Path,help='Existing etf-dashboard/dist directory');args=p.parse_args()
root=Path(__file__).resolve().parents[1]
for name in ('etf_momentum_latest.csv',):
    if not (args.source/name).is_file():raise SystemExit(f'Missing {name}')
for name in ('etf_momentum_latest.csv',):
    shutil.copy2(args.source/name,root/'dist'/name)
data=(root/'dist/etf_momentum_latest.csv').read_bytes()
rows=list(csv.DictReader(data.decode().splitlines()))
meta=dict(source='OpenD', adjustment='OpenD QFQ', asof=rows[0]['date'],
          generated_at=datetime.now(timezone.utc).isoformat(), count=len(rows), expected_count=71,
          sha256=hashlib.sha256(data).hexdigest(), benchmark='SPY', model='Hermes 20/60/120 v1')
(root/'dist/snapshot_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
subprocess.run([sys.executable,str(root/'scripts/validate_snapshot.py')],check=True)
print('Snapshot imported. To publish this complete source batch, dispatch with use_committed_snapshot=true.')

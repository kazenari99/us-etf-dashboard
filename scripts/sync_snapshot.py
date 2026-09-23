"""Copy an existing local US snapshot; never requests OpenD data."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
p=argparse.ArgumentParser();p.add_argument('source',type=Path,help='Existing etf-dashboard/dist directory');args=p.parse_args()
root=Path(__file__).resolve().parents[1]
for name in ('index.html','styles.css','app.js','etf_momentum_latest.csv'):
    if not (args.source/name).is_file():raise SystemExit(f'Missing {name}')
for name in ('index.html','styles.css','app.js','etf_momentum_latest.csv'):
    shutil.copy2(args.source/name,root/'dist'/name)
index=root/'dist/index.html';index.write_text(index.read_text().replace('ETF Momentum Radar','ORBIT PULSE').replace('HERMES / MARKET RESEARCH','HERMES / US ETF MOMENTUM'))
subprocess.run([sys.executable,str(root/'scripts/validate_snapshot.py')],check=True)
print('Snapshot copied. Commit and push to update GitHub Pages.')

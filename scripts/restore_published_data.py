"""Recover the latest successful Pages data without rolling back the current UI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ETF_FILES = ('etf_momentum_latest.csv', 'snapshot_meta.json')
AUX_FILES = ('stocks.json', 'stock_sectors.json', 'fund_profiles.json')

def gh(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))

def select_run(repo):
    runs = gh(f'repos/{repo}/actions/workflows/pages.yml/runs?branch=main&status=success&per_page=50')
    for run in runs['workflow_runs']:
        if (run['head_branch'] != 'main' or run['head_repository']['full_name'] != repo
                or run['path'] != '.github/workflows/pages.yml'):
            continue
        artifacts = gh(f'repos/{repo}/actions/runs/{run["id"]}/artifacts')['artifacts']
        if any(a['name'] == 'github-pages' and not a['expired'] for a in artifacts):
            return str(run['id'])
    raise RuntimeError('No successful Pages artifact available; refusing to roll data back to git')

def restore(archive, dist, stocks_only):
    wanted = (*ETF_FILES, *AUX_FILES)
    data = {}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            name = member.name.removeprefix('./')
            if name in wanted:
                if not member.isfile() or member.size > 20_000_000 or name in data:
                    raise ValueError('Invalid or duplicate snapshot member')
                data[name] = tar.extractfile(member).read()
    if any(name not in data for name in wanted):
        raise ValueError('Published artifact is missing snapshot files')
    meta = json.loads(data['snapshot_meta.json'])
    if hashlib.sha256(data['etf_momentum_latest.csv']).hexdigest() != meta['sha256']:
        raise ValueError('Published ETF checksum mismatch')
    for name in AUX_FILES:
        json.loads(data[name])
    for name in (wanted if stocks_only else AUX_FILES):
        (dist / name).write_bytes(data[name])
    # Reconcile this on every publication, even when only ETF data changes.
    reconcile(dist)
    return meta['asof']

def reconcile(dist):
    stocks = json.loads((dist / 'stocks.json').read_text())
    stocks['expected_session'] = json.loads((dist / 'snapshot_meta.json').read_text())['asof']
    (dist / 'stocks.json').write_text(json.dumps(stocks, ensure_ascii=False, indent=2) + '\n')

def main():
    repo = os.environ['GH_REPO']
    run_id = select_run(repo)
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(['gh', 'run', 'download', run_id, '--repo', repo, '--name',
                        'github-pages', '--dir', directory], check=True)
        session = restore(Path(directory) / 'artifact.tar', ROOT / 'dist',
                          os.environ.get('STOCKS_ONLY') == 'true')
    print(f'Restored published data from run {run_id}; previous ETF session {session}')

if __name__ == '__main__':
    if '--reconcile-only' in sys.argv:
        reconcile(ROOT / 'dist')
    else:
        main()

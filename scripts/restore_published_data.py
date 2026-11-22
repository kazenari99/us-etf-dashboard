"""Recover the latest successful Pages data without rolling back the current UI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ETF_FILES = ('etf_momentum_latest.csv', 'snapshot_meta.json')
AUX_FILES = ('stocks.json', 'stock_sectors.json', 'fund_profiles.json')
# Published only since score history was added; older artifacts lack it.
OPTIONAL_ETF_FILES = ('etf_history.json',)

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
    return None

def restore(archive, dist, stocks_only, keep_etf=False):
    wanted = (*ETF_FILES, *AUX_FILES, *OPTIONAL_ETF_FILES)
    data = {}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            name = member.name.removeprefix('./')
            if name in wanted:
                if not member.isfile() or member.size > 20_000_000 or name in data:
                    raise ValueError('Invalid or duplicate snapshot member')
                data[name] = tar.extractfile(member).read()
    return restore_files(data, dist, stocks_only, keep_etf)

def restore_files(data, dist, stocks_only, keep_etf=False):
    """Write published files into dist.

    ETF files are restored too, so a deferred or failed ETF refresh republishes the
    live snapshot rather than the stale copy committed in the repository. Only an
    explicitly imported snapshot (keep_etf) keeps the committed ETF files.
    """
    wanted = (*ETF_FILES, *AUX_FILES)
    if any(name not in data for name in wanted):
        raise ValueError('Published artifact is missing snapshot files')
    meta = json.loads(data['snapshot_meta.json'])
    if hashlib.sha256(data['etf_momentum_latest.csv']).hexdigest() != meta['sha256']:
        raise ValueError('Published ETF checksum mismatch')
    for name in AUX_FILES:
        json.loads(data[name])
    restore_etf = not (keep_etf and not stocks_only)
    for name in (wanted if restore_etf else AUX_FILES):
        (dist / name).write_bytes(data[name])
    for name in OPTIONAL_ETF_FILES:
        if restore_etf and name in data and json.loads(data[name]).get('asof') == meta['asof']:
            (dist / name).write_bytes(data[name])
        elif restore_etf:
            (dist / name).unlink(missing_ok=True)
    # Reconcile this on every publication, even when only ETF data changes.
    reconcile(dist)
    return meta['asof']

def reconcile(dist):
    stocks = json.loads((dist / 'stocks.json').read_text())
    stocks['expected_session'] = json.loads((dist / 'snapshot_meta.json').read_text())['asof']
    (dist / 'stocks.json').write_text(json.dumps(stocks, ensure_ascii=False, indent=2) + '\n')

def main():
    repo = os.environ['GH_REPO']
    keep_etf = os.environ.get('KEEP_COMMITTED_ETF') == 'true'
    run_id = select_run(repo)
    if run_id is None:
        # Pages artifacts expire quickly; the deployed mirror retains the same data.
        data = {}
        for name in (*ETF_FILES, *AUX_FILES):
            request = Request(f'https://kazenari99.github.io/us-etf-dashboard/{name}',
                              headers={'Cache-Control': 'no-cache'})
            with urlopen(request, timeout=30) as response:
                data[name] = response.read(20_000_001)
            if len(data[name]) > 20_000_000:
                raise ValueError('Published snapshot is too large')
        for name in OPTIONAL_ETF_FILES:
            try:
                with urlopen(Request(f'https://kazenari99.github.io/us-etf-dashboard/{name}',
                                     headers={'Cache-Control': 'no-cache'}), timeout=30) as response:
                    data[name] = response.read(20_000_001)
            except OSError:
                pass
        session = restore_files(data, ROOT / 'dist', os.environ.get('STOCKS_ONLY') == 'true', keep_etf)
        print(f'Restored verified live Pages mirror; previous ETF session {session}')
        write_output(session)
        return
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(['gh', 'run', 'download', run_id, '--repo', repo, '--name',
                        'github-pages', '--dir', directory], check=True)
        session = restore(Path(directory) / 'artifact.tar', ROOT / 'dist',
                          os.environ.get('STOCKS_ONLY') == 'true', keep_etf)
    print(f'Restored published data from run {run_id}; previous ETF session {session}')
    write_output(session)

def write_output(session):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f'asof={session}\n')

if __name__ == '__main__':
    if '--reconcile-only' in sys.argv:
        reconcile(ROOT / 'dist')
    else:
        main()

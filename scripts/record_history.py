"""Copy the ETF snapshot built by this run into the long-term history tree.

Usage: record_history.py RESEARCH_ARTIFACT_DIR HISTORY_DIR
Writes HISTORY_DIR/etf/<asof>.csv and .json and keeps HISTORY_DIR/etf/index.csv
sorted by session. Re-running for the same session replaces that session's files.
"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

INDEX_FIELDS = ('asof', 'generated_at', 'count', 'sha256', 'model', 'source')


def find_snapshot(source: Path):
    metas = sorted(p for p in source.rglob('snapshot_meta.json')
                   if (p.parent / 'etf_momentum_latest.csv').is_file())
    if not metas:
        raise SystemExit(f'No ETF snapshot in {source}')
    meta_path = max(metas, key=lambda p: json.loads(p.read_text())['generated_at'])
    meta = json.loads(meta_path.read_text())
    data = (meta_path.parent / 'etf_momentum_latest.csv').read_bytes()
    if hashlib.sha256(data).hexdigest() != meta['sha256']:
        raise SystemExit('Snapshot checksum mismatch; refusing to record history')
    return meta, data


def record(source: Path, history: Path):
    meta, data = find_snapshot(source)
    etf = history / 'etf'
    etf.mkdir(parents=True, exist_ok=True)
    asof = meta['asof']
    (etf / f'{asof}.csv').write_bytes(data)
    (etf / f'{asof}.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    index_path = etf / 'index.csv'
    rows = {}
    if index_path.exists():
        rows = {r['asof']: r for r in csv.DictReader(index_path.open())}
    rows[asof] = {k: meta.get(k, '') for k in INDEX_FIELDS}
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=INDEX_FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows[k] for k in sorted(rows))
    index_path.write_text(out.getvalue())
    print(f'Recorded ETF session {asof} ({meta["count"]} ETFs); {len(rows)} sessions in history')
    return asof


if __name__ == '__main__':
    record(Path(sys.argv[1]), Path(sys.argv[2]))

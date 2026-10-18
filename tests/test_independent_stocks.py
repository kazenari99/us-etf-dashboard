import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_refresh_day import route
import restore_published_data as restore

class IndependentStocksTests(unittest.TestCase):
    def test_stock_schedule_and_manual_do_not_depend_on_etf_calendar(self):
        for schedule in ('47 20 * * 1-5', '47 22 * * 1-5'):
            self.assertEqual(route('schedule', schedule, '', None), (True, True))
        self.assertEqual(route('workflow_dispatch', '', 'true', None), (True, True))
        self.assertEqual(route('schedule', '0 22 * * *', '', None), (False, False))
        self.assertEqual(route('schedule', '0 22 * * *', '', '2026-10-16'), (True, False))

    def artifact(self, directory, bad=False):
        csv = b'ticker,date\nSPY,2026-10-15\n'
        entries = {'etf_momentum_latest.csv':csv,
                   'snapshot_meta.json':json.dumps({'asof':'2026-10-15', 'sha256':hashlib.sha256(csv).hexdigest()}).encode(),
                   'stocks.json':json.dumps({'session_date':'2026-10-14', 'fetched_at':'original'}).encode(),
                   'stock_sectors.json':b'{}', 'fund_profiles.json':b'{}',
                   'index.html':b'old UI'}
        if bad:
            entries['etf_momentum_latest.csv'] = b'corrupted'
        archive = Path(directory) / 'artifact.tar'
        with tarfile.open(archive, 'w') as tar:
            for name, data in entries.items():
                info = tarfile.TarInfo('./'+name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return archive

    def test_stock_refresh_preserves_published_etf_and_current_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            (dist / 'index.html').write_text('current UI')
            restore.restore(self.artifact(directory), dist, True)
            self.assertEqual((dist / 'index.html').read_text(), 'current UI')
            self.assertIn('2026-10-15', (dist / 'etf_momentum_latest.csv').read_text())
            self.assertEqual(json.loads((dist / 'stocks.json').read_text())['fetched_at'], 'original')

    def test_etf_refresh_retains_stocks_and_reconciles_after_new_etf(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            (dist / 'snapshot_meta.json').write_text('{"asof":"2026-10-16"}')
            (dist / 'etf_momentum_latest.csv').write_text('new ETF')
            restore.restore(self.artifact(directory), dist, False)
            self.assertEqual((dist / 'etf_momentum_latest.csv').read_text(), 'new ETF')
            self.assertEqual(json.loads((dist / 'stocks.json').read_text())['expected_session'], '2026-10-16')

    def test_corrupt_artifact_cannot_overwrite_current_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            with self.assertRaisesRegex(ValueError, 'checksum'):
                restore.restore(self.artifact(directory, bad=True), dist, True)
            self.assertEqual(list(dist.iterdir()), [])

    def test_calendar_only_success_is_skipped_when_selecting_artifact(self):
        base = {'head_branch':'main', 'head_repository':{'full_name':'owner/repo'}, 'path':'.github/workflows/pages.yml'}
        with patch.object(restore, 'gh', side_effect=[
            {'workflow_runs':[dict(base,id=2),dict(base,id=1)]},
            {'artifacts':[]}, {'artifacts':[{'name':'github-pages','expired':False}]}]):
            self.assertEqual(restore.select_run('owner/repo'), '1')

    def test_expired_artifacts_allow_verified_live_mirror_fallback(self):
        base = {'head_branch':'main', 'head_repository':{'full_name':'owner/repo'}, 'path':'.github/workflows/pages.yml', 'id':1}
        with patch.object(restore, 'gh', side_effect=[{'workflow_runs':[base]},
                {'artifacts':[{'name':'github-pages','expired':True}]}]):
            self.assertIsNone(restore.select_run('owner/repo'))

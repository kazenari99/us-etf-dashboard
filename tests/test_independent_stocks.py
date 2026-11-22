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
        for schedule in ('17 21 * * 1-5', '17 23 * * 1-5'):
            self.assertEqual(route('schedule', schedule, '', None), (True, True))
        self.assertEqual(route('workflow_dispatch', '', 'true', None), (True, True))
        self.assertEqual(route('schedule', '0 6 * * *', '', None), (False, False))
        self.assertEqual(route('schedule', '0 6 * * *', '', '2026-10-22'), (True, False))
        self.assertEqual(route('schedule', '0 22 * * *', '', None), (False, False))
        self.assertEqual(route('schedule', '0 22 * * *', '', '2026-10-16'), (True, False))

    def test_worker_dispatch_is_gated_like_the_schedule_it_replaces(self):
        from check_refresh_day import effective_event
        self.assertEqual(effective_event('workflow_dispatch', '0 22 * * *'), 'schedule')
        self.assertEqual(effective_event('workflow_dispatch', ''), 'workflow_dispatch')
        self.assertEqual(effective_event('push', None), 'push')
        # A Worker-dispatched ETF run on an NYSE holiday is skipped, like the cron.
        self.assertEqual(route(effective_event('workflow_dispatch', '0 22 * * *'), '0 22 * * *', '', None),
                         (False, False))
        self.assertEqual(route(effective_event('workflow_dispatch', '17 21 * * 1-5'), '17 21 * * 1-5', '', None),
                         (True, True))

    def artifact(self, directory, bad=False, history=None):
        csv = b'ticker,date\nSPY,2026-10-15\n'
        entries = {'etf_momentum_latest.csv':csv,
                   'snapshot_meta.json':json.dumps({'asof':'2026-10-15', 'sha256':hashlib.sha256(csv).hexdigest()}).encode(),
                   'stocks.json':json.dumps({'session_date':'2026-10-14', 'fetched_at':'original'}).encode(),
                   'stock_sectors.json':b'{}', 'fund_profiles.json':b'{}',
                   'index.html':b'old UI'}
        if bad:
            entries['etf_momentum_latest.csv'] = b'corrupted'
        if history is not None:
            entries['etf_history.json'] = json.dumps(history).encode()
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

    def test_etf_run_restores_published_etf_so_deferral_cannot_roll_back(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            (dist / 'snapshot_meta.json').write_text('{"asof":"2026-09-25"}')
            (dist / 'etf_momentum_latest.csv').write_text('stale committed copy')
            self.assertEqual(restore.restore(self.artifact(directory), dist, False), '2026-10-15')
            self.assertIn('2026-10-15', (dist / 'etf_momentum_latest.csv').read_text())
            self.assertEqual(json.loads((dist / 'snapshot_meta.json').read_text())['asof'], '2026-10-15')

    def test_score_history_is_restored_only_when_it_matches_the_snapshot(self):
        for asof, kept in (('2026-10-15', True), ('2026-10-14', False)):
            with self.subTest(asof=asof), tempfile.TemporaryDirectory() as directory:
                dist = Path(directory) / 'dist'
                dist.mkdir()
                (dist / 'etf_history.json').write_text('{"asof":"stale"}')
                restore.restore(self.artifact(directory, history={'asof': asof}), dist, False)
                self.assertEqual((dist / 'etf_history.json').exists(), kept)

    def test_artifact_without_history_still_restores(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            self.assertEqual(restore.restore(self.artifact(directory), dist, True), '2026-10-15')
            self.assertFalse((dist / 'etf_history.json').exists())

    def test_imported_snapshot_is_kept_and_stocks_reconcile_to_it(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / 'dist'
            dist.mkdir()
            (dist / 'snapshot_meta.json').write_text('{"asof":"2026-10-16"}')
            (dist / 'etf_momentum_latest.csv').write_text('new ETF')
            restore.restore(self.artifact(directory), dist, False, keep_etf=True)
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

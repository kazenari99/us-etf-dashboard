import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_stock_sectors import sector_record


class SectorTests(unittest.TestCase):
    def test_fresh_cache_avoids_network(self):
        now = datetime.now(timezone.utc)
        prior = dict(sector='Healthcare', retrieved_at=now.isoformat(), status='ok')
        with patch('refresh_stock_sectors.yf.Ticker') as ticker:
            self.assertEqual(sector_record('TXG', prior, now), prior)
            ticker.assert_not_called()

    def test_failure_preserves_classification_and_date(self):
        now = datetime.now(timezone.utc)
        prior = dict(sector='Healthcare', retrieved_at=(now-timedelta(days=31)).isoformat())
        with patch('refresh_stock_sectors.yf.Ticker', side_effect=OSError):
            result = sector_record('TXG', prior, now)
            self.assertEqual(result, dict(prior, status='retained'))
            self.assertEqual(sector_record('UNKNOWN', {}, now), {'status':'unavailable'})

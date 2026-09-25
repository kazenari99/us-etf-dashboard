import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh_funds import validate_holdings,ark_holdings

class FundsTests(unittest.TestCase):
    def test_weight_is_fund_fraction_not_top_ten_normalized(self):
        r=validate_holdings([{'weight':.09},{'weight':.12}])
        self.assertEqual(r[0]['weight'],.12)
        self.assertAlmostEqual(sum(x['weight'] for x in r),.21)
    def test_bad_weights_rejected(self):
        for w in (-.1,1.5,float('nan')):
            with self.assertRaises(ValueError):validate_holdings([{'weight':w}])
    def test_official_dates_and_percent_units(self):
        text='date,fund,company,ticker,weight (%)\n09/25/2026,ARKK,Tesla,TSLA,9.17%\n'
        rows,date=ark_holdings(text)
        self.assertEqual(date,'2026-09-25');self.assertAlmostEqual(rows[0]['weight'],.0917)
        with self.assertRaises(ValueError):ark_holdings(text+'09/24/2026,ARKK,Other,X,2%\n')

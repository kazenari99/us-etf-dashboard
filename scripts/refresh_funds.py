"""Public fund context, refreshed independently of price bars; never invent as-of dates."""
import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import requests
import yfinance as yf
from momentum import UNIVERSE

ROOT = Path(__file__).resolve().parents[1]
ARK_URL = 'https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv'

def validate_holdings(rows):
    if not rows:
        return []
    if any(not math.isfinite(r['weight']) or not 0 <= r['weight'] <= 1 for r in rows):
        raise ValueError('Invalid holding weights')
    if sum(r['weight'] for r in rows) > 1.02:
        raise ValueError('Unexpected long-only holdings total')
    return sorted(rows, key=lambda r: r['weight'], reverse=True)[:10]

def ark_holdings(text):
    records = list(csv.DictReader(io.StringIO(text)))
    records = [r for r in records if r.get('fund') == 'ARKK']
    dates = {datetime.strptime(r['date'], '%m/%d/%Y').date().isoformat() for r in records}
    if len(dates) != 1:
        raise ValueError('Missing or mixed ARK holdings dates')
    rows = [{'symbol':r['ticker'] or '—', 'name':r['company'],
             'weight':float(r['weight (%)'].replace('%','').replace(',',''))/100} for r in records]
    return validate_holdings(rows), dates.pop()

def main():
    path = ROOT/'dist/fund_profiles.json'
    previous = json.loads(path.read_text()).get('funds', {}) if path.exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    funds = {}
    yf.set_tz_cache_location(str(ROOT/'.cache/yfinance'))
    for ticker in sorted({t for ts in UNIVERSE.values() for t in ts.split()}):
        prior = previous.get(ticker, {})
        item = dict(prior)
        item.update(last_attempt_at=now, refresh_error=None)
        try:
            f = yf.Ticker(ticker).funds_data
            description = f.description
            overview = f.fund_overview
            raw = f.top_holdings
            holdings = validate_holdings([{'symbol':str(symbol), 'name':str(row['Name']),
                                          'weight':float(row['Holding Percent'])} for symbol,row in raw.iterrows()])
            item.update(description=description or prior.get('description',''),
                        family=overview.get('family'), category=overview.get('categoryName'),
                        profile_source=f'https://finance.yahoo.com/quote/{ticker}/profile/',
                        profile_retrieved_at=now)
            if holdings:
                item.update(holdings=holdings, holdings_asof=None, holdings_retrieved_at=now,
                            holdings_source=f'https://finance.yahoo.com/quote/{ticker}/holdings/',
                            holdings_provider='Yahoo Finance', holdings_status='date_unknown')
            elif prior.get('holdings'):
                item['holdings_status']='retained'
            else:
                item.update(holdings=[],holdings_status='unavailable')
        except Exception as exc:
            item.update(refresh_error=type(exc).__name__,holdings_status='retained' if prior.get('holdings') else 'unavailable')
        if ticker == 'ARKK':
            item['summary_zh']='主动管理的创新主题股票ETF，关注颠覆性技术相关公司。持仓可跨行业及国家，组合集中，收益对成长股估值与经理选股较敏感。'
            item['summary_source']='https://www.ark-funds.com/funds/arkk'
            try:
                response=requests.get(ARK_URL,timeout=25);response.raise_for_status()
                holdings,asof=ark_holdings(response.text)
                item.update(holdings=holdings,holdings_asof=asof,holdings_retrieved_at=now,
                            holdings_source=ARK_URL,holdings_provider='ARK 官方',holdings_status='dated')
            except Exception:
                # Keep a prior dated official batch instead of silently replacing it.
                if prior.get('holdings_provider') == 'ARK 官方':
                    for k in ('holdings','holdings_asof','holdings_retrieved_at','holdings_source','holdings_provider'):
                        item[k]=prior[k]
                    item['holdings_status']='retained'
        funds[ticker]=item
        print(ticker,item.get('holdings_status'),len(item.get('holdings',[])),flush=True)
    payload={'generated_at':now,'funds':funds}
    text=json.dumps(payload,ensure_ascii=False,allow_nan=False,indent=2)+'\n'
    temp=path.with_suffix('.tmp');temp.write_text(text);temp.replace(path)
    archive=ROOT/'archive/fund_profiles'/datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    archive.mkdir(parents=True,exist_ok=True);(archive/'fund_profiles.json').write_text(text)

if __name__=='__main__':
    main()

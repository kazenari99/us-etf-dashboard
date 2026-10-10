"""Cache public Yahoo Finance sector classifications independently of prices."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]


def sector_record(ticker, previous, now):
    try:
        fetched = datetime.fromisoformat(previous.get('retrieved_at', ''))
        if previous.get('sector') and now - fetched < timedelta(days=30):
            return previous
    except (ValueError, TypeError):
        pass
    try:
        sector = yf.Ticker(ticker).get_info().get('sector')
        if isinstance(sector, str) and sector.strip():
            return {'sector': sector.strip(), 'retrieved_at': now.isoformat(),
                    'source': 'Yahoo Finance', 'status': 'ok'}
    except Exception:
        pass
    return dict(previous, status='retained' if previous.get('sector') else 'unavailable')


def main():
    path = ROOT / 'dist/stock_sectors.json'
    cached = json.loads(path.read_text()) if path.exists() else {}
    try:
        with urlopen('https://orbit-us.pages.dev/stock_sectors.json', timeout=20) as response:
            deployed = json.load(response)
        for ticker, record in deployed.items():
            if record.get('retrieved_at', '') > cached.get(ticker, {}).get('retrieved_at', ''):
                cached[ticker] = record
    except Exception:
        pass
    tickers = [s['ticker'] for s in json.loads((ROOT / 'dist/stocks.json').read_text())['stocks']]
    now = datetime.now(timezone.utc)
    yf.set_tz_cache_location(str(ROOT / '.cache/yfinance'))
    def fetch(ticker):
        return ticker, sector_record(ticker, cached.get(ticker, {}), now)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(pool.map(fetch, tickers))
    cached.update(records)
    path.write_text(json.dumps(cached, ensure_ascii=False, indent=2) + '\n')
    print(f'Sectors: {sum(bool(r.get("sector")) for r in records.values())}/{len(tickers)}')


if __name__ == '__main__':
    main()

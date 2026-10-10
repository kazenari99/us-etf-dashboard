"""Mirror the author's public candidate snapshot, never their private database."""
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
import pandas_market_calendars as mcal

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://anish1294.github.io/minervini-trend-template-screener/current.json'


def previous_tokyo_session(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Timezone required')
    day = now.astimezone(ZoneInfo('Asia/Tokyo')).date() - timedelta(days=1)
    sessions = mcal.get_calendar('NYSE').schedule(start_date=day, end_date=day)
    return day.isoformat() if not sessions.empty else None


def validate(payload):
    rows = payload.get('stocks')
    if not isinstance(rows, list) or not rows or len(rows) > 300:
        raise ValueError('Invalid public candidate universe')
    if payload.get('count') != len(rows):
        raise ValueError('Count mismatch')
    session = datetime.strptime(payload['session_date'], '%Y-%m-%d').date()
    if session > datetime.now(ZoneInfo('America/New_York')).date():
        raise ValueError('Future session')
    tickers = [r.get('ticker') for r in rows]
    if not all(isinstance(t, str) and t for t in tickers) or len(set(tickers)) != len(rows):
        raise ValueError('Invalid tickers')
    return payload


def matches(row):
    keys = ('rs_rating', 'below_52w_high_pct', 'volume_ratio')
    if not all(isinstance(row.get(k), (int, float)) and not isinstance(row[k], bool)
               and math.isfinite(row[k]) for k in keys):
        return False
    return row['rs_rating'] >= 90 and row['below_52w_high_pct'] <= 25 and row['volume_ratio'] >= 1


def refresh():
    path = ROOT / 'dist/stocks.json'
    now = datetime.now(timezone.utc)
    expected = json.loads((ROOT / 'dist/snapshot_meta.json').read_text())['asof']
    previous = json.loads(path.read_text()) if path.exists() else {}
    # Actions starts from git, while newer successful snapshots live in Pages artifacts.
    # Recover the deployed copy before replacing it, so failures cannot roll data back.
    try:
        with urlopen('https://orbit-us.pages.dev/stocks.json', timeout=20) as response:
            deployed = validate(json.load(response))
        if deployed['session_date'] >= previous.get('session_date', ''):
            previous = deployed
    except Exception:
        pass
    try:
        with urlopen(SOURCE, timeout=30) as response:
            payload = validate(json.load(response))
        if payload['session_date'] < previous.get('session_date', ''):
            raise ValueError('Source session regressed')
        payload.update(source_url=SOURCE, fetched_at=now.isoformat(), expected_session=expected,
                       fetch_status='ok', fetch_error=None)
    except Exception as exc:
        payload = previous or {'stocks': [], 'count': 0, 'session_date': None, 'source_url': SOURCE}
        payload.update(fetch_status='failed', fetch_error=type(exc).__name__, expected_session=expected)
        print(f'Public stock refresh failed; retaining dated snapshot: {type(exc).__name__}')
    payload['checked_at'] = now.isoformat()
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2))
    temporary.replace(path)
    print(f"Stocks: {payload.get('session_date')}, {payload['count']} candidates, status={payload['fetch_status']}")


if __name__ == '__main__':
    refresh()

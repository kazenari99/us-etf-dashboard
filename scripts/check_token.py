"""Warn before the scheduler's GitHub token expires.

Calls the GitHub API with GH_DISPATCH_TOKEN and reads the
`GitHub-Authentication-Token-Expiration` response header (fine-grained and
classic tokens with an expiry send it). Writes `alert=true|false` and a
markdown report (TOKEN_REPORT, default token.md). The token is never printed.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

WARN_DAYS = 14


def parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S %Z', '%Y-%m-%d %H:%M:%S %z'):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f'Unrecognised token expiry header: {value!r}')


def evaluate(status: int, expiry: datetime | None, now: datetime) -> tuple[bool, str]:
    if status in (401, 403):
        return True, ('`GH_DISPATCH_TOKEN` was **rejected** by GitHub (HTTP %d): it has expired, been revoked, '
                      'or lost Actions access. The on-time scheduler is not dispatching; GitHub\'s own late '
                      'schedule is still running.' % status)
    if status != 200:
        return False, f'GitHub API answered HTTP {status}; token state unknown, will check again tomorrow.'
    if expiry is None:
        return False, '`GH_DISPATCH_TOKEN` has no expiry date.'
    days = (expiry - now).total_seconds() / 86400
    when = expiry.strftime('%Y-%m-%d %H:%M UTC')
    if days <= WARN_DAYS:
        return True, (f'`GH_DISPATCH_TOKEN` expires on **{when}** ({max(days, 0):.0f} days left). '
                      'Generate a new fine-grained token (this repository only, Actions: Read and write) and '
                      'replace the repository secret before then; the Worker reads it on its next deploy, so '
                      'also re-run **Deploy scheduler Worker**.')
    return False, f'`GH_DISPATCH_TOKEN` expires on {when} ({days:.0f} days left).'


def main():
    token = os.environ.get('GH_DISPATCH_TOKEN', '')
    repo = os.environ.get('GITHUB_REPOSITORY', 'kazenari99/us-etf-dashboard')
    if not token:
        alert, text = False, '`GH_DISPATCH_TOKEN` is not set; the scheduler Worker is not in use.'
    else:
        request = Request(f'https://api.github.com/repos/{repo}', headers={
            'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
            'User-Agent': 'us-etf-dashboard-token-check'})
        try:
            with urlopen(request, timeout=30) as response:
                status, header = response.status, response.headers.get('GitHub-Authentication-Token-Expiration')
        except HTTPError as exc:
            status, header = exc.code, None
        alert, text = evaluate(status, parse_expiry(header), datetime.now(timezone.utc))
    print(text)
    with open(os.environ.get('TOKEN_REPORT', 'token.md'), 'w') as out:
        out.write(text + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f'alert={str(alert).lower()}\n')


if __name__ == '__main__':
    main()

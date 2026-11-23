"""Gate scheduled runs by the previous Tokyo calendar date's NYSE session."""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from refresh_stocks import previous_tokyo_session

# How far back an on-time run counts as covering a late GitHub fallback.
COVER_HOURS = 20

STOCK_SCHEDULES = {'17 21 * * 1-5', '17 23 * * 1-5'}

def route(event, schedule, manual_stocks, session):
    stocks_only = (event == 'schedule' and schedule in STOCK_SCHEDULES) or (
        event == 'workflow_dispatch' and manual_stocks == 'true')
    run = stocks_only or event != 'schedule' or session is not None
    return run, stocks_only

def effective_event(event, schedule):
    """The scheduler Worker dispatches with the GitHub cron it replaces; gate it like a schedule."""
    return 'schedule' if event == 'workflow_dispatch' and schedule else event

def covered_by_on_time_run(runs, schedule, now, hours=COVER_HOURS):
    """True if the scheduler Worker's run for this schedule already succeeded recently."""
    for run in runs:
        created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
        if (run.get('event') == 'workflow_dispatch' and run.get('conclusion') == 'success'
                and run.get('display_title') == f'On-time {schedule}'
                and now - created <= timedelta(hours=hours)):
            return True
    return False


def recent_runs(repo):
    out = subprocess.check_output(['gh', 'api', f'repos/{repo}/actions/workflows/pages.yml/runs'
                                   '?event=workflow_dispatch&status=success&per_page=30'], text=True)
    return json.loads(out)['workflow_runs']


if __name__ == '__main__':
    session = previous_tokyo_session()
    raw_event = os.environ.get('GITHUB_EVENT_NAME')
    schedule = os.environ.get('REFRESH_SCHEDULE')
    event = effective_event(raw_event, schedule)
    run, stocks = route(event, schedule, os.environ.get('STOCKS_ONLY'), session)
    if run and raw_event == 'schedule' and os.environ.get('GH_REPO'):
        # GitHub's own cron is only a fallback now; skip it when the Worker already ran on time.
        try:
            if covered_by_on_time_run(recent_runs(os.environ['GH_REPO']), schedule, datetime.now(timezone.utc)):
                run = False
                print(f'::notice title=Fallback skipped::The on-time run for "{schedule}" already succeeded.')
        except (subprocess.CalledProcessError, KeyError, ValueError) as exc:
            print(f'Could not check on-time runs ({type(exc).__name__}); running the fallback.')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f"run={str(run).lower()}\nstocks_only={str(stocks).lower()}\n")
    print(f'Previous Tokyo date NYSE session: {session}; refresh={run}; stocks_only={stocks}')

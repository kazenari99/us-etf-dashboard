"""Gate scheduled runs by the previous Tokyo calendar date's NYSE session."""
import os
from refresh_stocks import previous_tokyo_session

STOCK_SCHEDULES = {'17 21 * * 1-5', '17 23 * * 1-5'}

def route(event, schedule, manual_stocks, session):
    stocks_only = (event == 'schedule' and schedule in STOCK_SCHEDULES) or (
        event == 'workflow_dispatch' and manual_stocks == 'true')
    run = stocks_only or event != 'schedule' or session is not None
    return run, stocks_only

if __name__ == '__main__':
    session = previous_tokyo_session()
    run, stocks = route(os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('REFRESH_SCHEDULE'),
                        os.environ.get('STOCKS_ONLY'), session)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f"run={str(run).lower()}\nstocks_only={str(stocks).lower()}\n")
    print(f'Previous Tokyo date NYSE session: {session}; refresh={run}; stocks_only={stocks}')

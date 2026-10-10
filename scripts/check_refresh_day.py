"""Gate scheduled runs by the previous Tokyo calendar date's NYSE session."""
import os
from refresh_stocks import previous_tokyo_session

session = previous_tokyo_session()
run = os.environ.get('GITHUB_EVENT_NAME') != 'schedule' or session is not None
with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
    output.write(f"run={'true' if run else 'false'}\n")
print(f'Previous Tokyo date NYSE session: {session}; refresh={run}')

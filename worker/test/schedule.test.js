import { test } from 'node:test';
import assert from 'node:assert/strict';
import { dueSchedules, dispatch } from '../src/index.js';

const at = (iso) => dueSchedules(new Date(iso));

test('ETF runs fire at 22:00 and 06:00 UTC every day', () => {
  assert.deepEqual(at('2026-11-22T22:00:00Z'), ['0 22 * * *']);
  assert.deepEqual(at('2026-11-23T06:00:00Z'), ['0 6 * * *']);
  assert.deepEqual(at('2026-11-22T21:00:00Z'), []);
});

test('stock runs follow New York time across DST', () => {
  // EST (UTC-5): Mon 21:17 NY = Tue 02:17 UTC; 01:17 UTC is 20:17 NY.
  assert.deepEqual(at('2026-11-24T02:17:00Z'), ['17 21 * * 1-5']);
  assert.deepEqual(at('2026-11-24T01:17:00Z'), []);
  assert.deepEqual(at('2026-11-24T04:17:00Z'), ['17 23 * * 1-5']);
  // EDT (UTC-4): Mon 2026-07-06 21:17 NY = Tue 01:17 UTC.
  assert.deepEqual(at('2026-07-07T01:17:00Z'), ['17 21 * * 1-5']);
  assert.deepEqual(at('2026-07-07T03:17:00Z'), ['17 23 * * 1-5']);
});

test('stock runs skip New York weekends', () => {
  // Sat 2026-11-21 21:17 NY = Sun 02:17 UTC.
  assert.deepEqual(at('2026-11-22T02:17:00Z'), []);
  // Fri 2026-11-20 21:17 NY = Sat 02:17 UTC still runs.
  assert.deepEqual(at('2026-11-21T02:17:00Z'), ['17 21 * * 1-5']);
});

test('every Worker cron minute maps to at most one schedule and covers all four', async () => {
  const seen = new Set();
  for (let day = 0; day < 370; day += 1) {
    for (const [h, m] of [[6, 0], [22, 0], [1, 17], [2, 17], [3, 17], [4, 17]]) {
      const d = new Date(Date.UTC(2026, 0, 1 + day, h, m));
      const due = dueSchedules(d);
      assert.ok(due.length <= 1);
      due.forEach((c) => seen.add(c));
    }
  }
  assert.equal(seen.size, 4);
});

test('dispatch posts the schedule and fails loudly without leaking the token', async () => {
  const calls = [];
  const env = { GH_REPO: 'o/r', WORKFLOW: 'pages.yml', GH_DISPATCH_TOKEN: 'secret-token' };
  await dispatch(env, '0 22 * * *', async (url, init) => { calls.push([url, init]); return { status: 204 }; });
  assert.equal(calls[0][0], 'https://api.github.com/repos/o/r/actions/workflows/pages.yml/dispatches');
  assert.deepEqual(JSON.parse(calls[0][1].body), { ref: 'main', inputs: { schedule: '0 22 * * *' } });
  await assert.rejects(
    dispatch(env, '0 6 * * *', async () => ({ status: 403 })),
    (err) => err.message.includes('HTTP 403') && !err.message.includes('secret-token'),
  );
});

// Dispatches the Publish workflow on time. GitHub's own `schedule` often starts
// hours late; this Worker fires at the exact minute and passes the matching
// GitHub cron string, so the workflow's calendar gate treats it like a schedule.

// Same cron strings as .github/workflows/pages.yml, with the wall-clock time they mean.
export const SCHEDULES = [
  { cron: '0 22 * * *', timeZone: 'UTC', hour: 22, minute: 0 },
  { cron: '0 6 * * *', timeZone: 'UTC', hour: 6, minute: 0 },
  { cron: '17 21 * * 1-5', timeZone: 'America/New_York', hour: 21, minute: 17, weekdays: true },
  { cron: '17 23 * * 1-5', timeZone: 'America/New_York', hour: 23, minute: 17, weekdays: true },
];

function localParts(date, timeZone) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone, hour: 'numeric', minute: 'numeric', weekday: 'short', hourCycle: 'h23',
  }).formatToParts(date);
  const get = (type) => parts.find((p) => p.type === type).value;
  return { hour: Number(get('hour')), minute: Number(get('minute')), weekday: get('weekday') };
}

/** GitHub cron strings due at `date` (a Date at the trigger's scheduled minute). */
export function dueSchedules(date) {
  return SCHEDULES.filter((s) => {
    const t = localParts(date, s.timeZone);
    if (t.hour !== s.hour || t.minute !== s.minute) return false;
    return !s.weekdays || !['Sat', 'Sun'].includes(t.weekday);
  }).map((s) => s.cron);
}

export async function dispatch(env, schedule, fetchImpl = fetch) {
  const url = `https://api.github.com/repos/${env.GH_REPO}/actions/workflows/${env.WORKFLOW}/dispatches`;
  const response = await fetchImpl(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'us-etf-scheduler',
    },
    body: JSON.stringify({ ref: 'main', inputs: { schedule } }),
  });
  if (response.status !== 204) {
    // Status only: the body can echo request details and the token must never be logged.
    throw new Error(`GitHub dispatch for "${schedule}" failed: HTTP ${response.status}`);
  }
}

export default {
  async scheduled(event, env) {
    if (!env.GH_DISPATCH_TOKEN) throw new Error('GH_DISPATCH_TOKEN secret is not set');
    const due = dueSchedules(new Date(event.scheduledTime));
    for (const schedule of due) {
      await dispatch(env, schedule);
      console.log(`Dispatched ${env.WORKFLOW} for "${schedule}"`);
    }
    if (!due.length) console.log(`Nothing due at ${new Date(event.scheduledTime).toISOString()}`);
  },
  async fetch() {
    return new Response('Not found', { status: 404 });
  },
};

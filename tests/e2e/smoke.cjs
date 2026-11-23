// Browser smoke test: open the built sites on desktop and phone, in zh/en/ja,
// and fail on any console error or broken core interaction.
// Usage: node tests/e2e/smoke.cjs <base-url-of-current> <base-url-of-legacy>
const { chromium, devices } = require('playwright');
const assert = require('node:assert/strict');

(async () => {

const [current, legacy] = process.argv.slice(2);
const failures = [];
const step = async (name, fn) => {
  try { await fn(); console.log(`ok   ${name}`); }
  catch (err) { failures.push(name); console.log(`FAIL ${name}\n     ${err.message.split('\n')[0]}`); }
};

async function open(browser, url, { lang = 'zh', phone = false } = {}) {
  const context = await browser.newContext(phone ? { ...devices['iPhone 13'] } : { viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => {
    if (m.type() !== 'error') return;
    // etf_history.json is optional; older snapshots legitimately 404 on it.
    if (/status of 404/.test(m.text()) && /etf_history\.json/.test(m.location().url || '')) return;
    errors.push(m.text());
  });
  await page.addInitScript(l => { try { localStorage.setItem('orbit-language', l); } catch {} }, lang);
  await page.goto(url);
  await page.waitForSelector('#tableBody tr', { timeout: 15000 });
  await page.waitForTimeout(400);
  return { page, errors, close: () => context.close() };
}

const browser = await chromium.launch();

for (const lang of ['zh', 'en', 'ja']) {
  await step(`desktop ${lang}: renders 80 ETFs with history, regime and no errors`, async () => {
    const { page, errors, close } = await open(browser, current, { lang });
    assert.equal(await page.$$eval('#tableBody tr', r => r.length), 80);
    assert.notEqual((await page.textContent('#regimeTitle')).trim(), '');
    assert.match(await page.textContent('#tableBody tr:first-child'), /[↑↓=]/);
    assert.ok(await page.$('.peer-tag'), 'correlated cluster should be tagged in leaders');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    assert.equal(overflow, 0, 'page scrolls sideways');
    assert.deepEqual(errors, []);
    await close();
  });
}

await step('desktop: row opens drawer with sparkline; star filter keeps only starred', async () => {
  const { page, errors, close } = await open(browser, current);
  await page.click('#tableBody tr:nth-child(2) td:nth-child(3)');
  await page.waitForSelector('.history-block svg.spark', { timeout: 5000 });
  await page.keyboard.press('Escape');
  await page.click('#tableBody tr:first-child .etf-star');
  await page.click('#setupFilter [data-setup="starred"]');
  assert.equal(await page.$$eval('#tableBody tr', r => r.length), 1);
  assert.deepEqual(errors, []);
  await close();
});

await step('phone: four key columns, toggle shows all, no sideways page scroll', async () => {
  const { page, errors, close } = await open(browser, current, { phone: true });
  const visible = () => page.$$eval('#etfView thead th', t => t.filter(th => getComputedStyle(th).display !== 'none').length);
  assert.equal(await visible(), 4);
  await page.click('#colToggle');
  assert.equal(await visible(), 13);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth), 0);
  assert.deepEqual(errors, []);
  await close();
});

await step('legacy snapshot without history still renders', async () => {
  const { page, errors, close } = await open(browser, legacy);
  assert.ok(await page.$$eval('#tableBody tr', r => r.length) > 0);
  assert.notEqual((await page.textContent('#regimeTitle')).trim(), '');
  assert.deepEqual(errors, []);
  await close();
});

await step('stock screener tab renders', async () => {
  const { page, errors, close } = await open(browser, current);
  await page.click('[data-view="stocks"]');
  await page.waitForSelector('#stockRows tr', { timeout: 10000 });
  assert.deepEqual(errors, []);
  await close();
});

await browser.close();
if (failures.length) { console.log(`\n${failures.length} smoke check(s) failed`); process.exit(1); }
console.log('\nAll smoke checks passed');
})().catch(err => { console.error(err); process.exit(1); });

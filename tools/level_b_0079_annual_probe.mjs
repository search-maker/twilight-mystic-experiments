import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const BASE_URL = process.env.DEPLOYMENT_URL;
const APPLICATION_SHA = process.env.APPLICATION_SHA;
const OUTPUT = process.env.ANNUAL_PROBE_OUTPUT || '0079-annual-probe.json';
const ENGINE = 'level-b-v3-crumey-blackwell-transient-experimental';
const POLL_MS = 5000;
const STALL_MS = 600000;
const TOTAL_MS = 2100000;
if (!BASE_URL || !APPLICATION_SHA) throw new Error('DEPLOYMENT_URL and APPLICATION_SHA are required');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const report = {
  schemaVersion: 1,
  mysticState: 'MYSTIC-STATE-0079',
  purpose: 'annual-worker-heartbeat-diagnosis',
  applicationSha: APPLICATION_SHA,
  deploymentUrl: BASE_URL,
  engine: ENGINE,
  period: '2026-08',
  cadence: 'weekly',
  pollMs: POLL_MS,
  stallMs: STALL_MS,
  totalMs: TOTAL_MS,
  samples: [],
  consoleErrors: [],
  pageErrors: [],
  pass: false,
  claimBoundary: 'software-orchestration-diagnosis-only-not-empirical-real-sky-or-human-validation',
};

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
const page = await context.newPage();
page.setDefaultTimeout(240000);
page.setDefaultNavigationTimeout(120000);
page.on('console', msg => {
  if (msg.type() !== 'error') return;
  const location = msg.location?.() || {};
  const text = msg.text();
  const url = location.url || '';
  if (/cloudflareinsights\.com\/cdn-cgi\/rum|\/cdn-cgi\/rum/i.test(`${text} ${url}`)) return;
  report.consoleErrors.push({ text, url, lineNumber: location.lineNumber ?? null });
});
page.on('pageerror', error => report.pageErrors.push(error?.stack || error?.message || String(error)));

async function waitCalculateReady(timeout = 600000) {
  await page.waitForFunction(() => {
    const b = document.querySelector('#calculate');
    return Boolean(b && !b.disabled && b.getAttribute('aria-busy') !== 'true' && !b.classList.contains('is-calculating'));
  }, undefined, { timeout });
}

async function annualState() {
  return page.evaluate(() => {
    const lexical = expression => {
      try { return window.eval(expression); } catch { return null; }
    };
    const rows = typeof annualResults !== 'undefined' && Array.isArray(annualResults) ? annualResults : [];
    const cancel = document.querySelector('#cancelAnnual');
    const calculate = document.querySelector('#calculateAnnual');
    const cancelVisible = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && getComputedStyle(cancel).visibility !== 'hidden' && !cancel.disabled);
    const activeWorker = lexical("typeof activeAnnualWorker !== 'undefined' ? activeAnnualWorker : null");
    const version = Number(lexical("typeof annualCalculationVersion !== 'undefined' ? annualCalculationVersion : NaN"));
    const final = typeof annualResultsFinal !== 'undefined' ? annualResultsFinal : null;
    const engineOf = row => row?.calculationEngine ?? row?.levelBRunProvenance?.calculationEngine ?? null;
    const atmosphereUnavailableDates = rows
      .filter(row => row?.reason === 'LEVEL_B_ATMOSPHERE_UNAVAILABLE')
      .map(row => ({
        date: row?.date ?? null,
        errorCode: row?.errorCode ?? null,
        errorMessage: row?.errorMessage ?? null,
        diagnostic: row?.levelBAtmosphereDiagnostic ?? null,
      }));
    return {
      at: new Date().toISOString(),
      final,
      length: rows.length,
      pending: rows.filter(row => Boolean(row?.pending)).length,
      provisional: rows.filter(row => Boolean(row?.provisional)).length,
      verified: rows.filter(row => row && !row.pending && row.provisional === false).length,
      engines: [...new Set(rows.map(engineOf).filter(Boolean))],
      atmosphereUnavailableDates,
      progressValue: Number(document.querySelector('#annualProgressBar')?.value ?? 0),
      progressText: String(document.querySelector('#annualProgressText')?.textContent || '').trim().slice(0, 500),
      calculateDisabled: calculate?.disabled ?? null,
      cancelVisible,
      activeWorker: activeWorker == null ? null : Boolean(activeWorker),
      version: Number.isFinite(version) ? version : null,
      exportCsvEnabled: document.querySelector('#exportAnnualCsv')?.disabled === false,
      errorText: String(document.querySelector('#error')?.textContent || '').trim().slice(0, 500),
    };
  });
}

function isTerminal(s) {
  return s.final === true && s.length >= 4 && s.length <= 6 && s.pending === 0 && s.provisional === 0 && s.verified === s.length && s.calculateDisabled === false && s.cancelVisible === false && s.activeWorker !== true;
}
function isSilentAbort(s) {
  return s.final === true && s.length === 0 && s.activeWorker !== true && s.calculateDisabled === false && s.cancelVisible === false;
}
function heartbeatKey(s) {
  return JSON.stringify([s.verified, s.pending, s.provisional, s.progressValue, s.progressText]);
}

try {
  const markerResponse = await fetch(new URL('/level-b-software-status.json', BASE_URL));
  assert(markerResponse.ok, `deployment marker HTTP ${markerResponse.status}`);
  const marker = await markerResponse.json();
  report.deploymentMarker = marker;
  assert(marker.commitSha === APPLICATION_SHA, `deployment marker SHA mismatch: ${marker.commitSha}`);

  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { state: 'visible', timeout: 60000 });
  await waitCalculateReady();
  await page.evaluate(() => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    set('lat', 31.778);
    set('lon', 35.235);
    set('observerElevationM', 754);
    set('timezone', 'Asia/Jerusalem');
    set('date', '2026-08-17');
  });
  await page.selectOption('#visibilityEngineMode', ENGINE);
  await waitCalculateReady();
  await page.click('#threeStarCalculatorTab');
  await page.waitForFunction(() => document.querySelector('#calculatorFeature')?.value === 'three-star', undefined, { timeout: 60000 });
  await page.click('#calculate');
  await waitCalculateReady();
  const baseline = await page.evaluate(() => {
    try { return JSON.parse(JSON.stringify(window.eval('threeStarResultData'))); } catch { return null; }
  });
  report.baseline = baseline;
  assert(baseline && baseline.calculationEngine === ENGINE, 'transient Three-Star baseline did not bind exact engine');

  const annual = page.locator('#annualView');
  await annual.waitFor({ state: 'visible', timeout: 60000 });
  if (!(await annual.evaluate(el => el.open))) {
    await annual.locator('summary').click();
    await page.waitForFunction(() => document.querySelector('#annualView')?.open === true, undefined, { timeout: 10000 });
  }
  await page.evaluate(() => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.value = value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    set('annualCalendar', 'gregorian-month');
    set('annualMonth', '2026-08');
    set('annualCadence', 'weekly');
  });

  const before = await annualState();
  report.beforeStart = before;
  const baselineVersion = Number.isFinite(before.version) ? before.version : -1;
  assert(before.activeWorker !== true && before.cancelVisible === false && before.calculateDisabled === false, `Annual not idle before single start: ${JSON.stringify(before)}`);
  await page.click('#calculateAnnual');

  let state = await annualState();
  const startDeadline = Date.now() + 15000;
  while (Date.now() < startDeadline && !(isTerminal(state) || (state.final === false && state.length >= 4 && state.length <= 6 && state.pending > 0 && state.activeWorker === true && state.version > baselineVersion))) {
    await page.waitForTimeout(500);
    state = await annualState();
  }
  assert(isTerminal(state) || (state.final === false && state.length >= 4 && state.length <= 6 && state.pending > 0 && state.activeWorker === true && state.version > baselineVersion), `Annual did not enter stable worker-backed state: ${JSON.stringify(state)}`);

  const startedAt = Date.now();
  let lastHeartbeatAt = startedAt;
  let lastKey = heartbeatKey(state);
  report.samples.push({ elapsedMs: 0, ...state });

  while (!isTerminal(state)) {
    if (isSilentAbort(state)) throw new Error(`Annual silent abort: ${JSON.stringify(state)}`);
    if (state.errorText) throw new Error(`Annual application error: ${state.errorText}`);
    const elapsed = Date.now() - startedAt;
    if (elapsed > TOTAL_MS) throw new Error(`Annual total diagnostic cap exceeded after ${elapsed} ms: ${JSON.stringify(state)}`);
    if (state.activeWorker === true && Date.now() - lastHeartbeatAt > STALL_MS) {
      throw new Error(`Annual worker stall: no heartbeat for ${Date.now() - lastHeartbeatAt} ms: ${JSON.stringify(state)}`);
    }
    await page.waitForTimeout(POLL_MS);
    const next = await annualState();
    const key = heartbeatKey(next);
    if (key !== lastKey) {
      lastHeartbeatAt = Date.now();
      lastKey = key;
      report.samples.push({ elapsedMs: Date.now() - startedAt, ...next });
      console.log(JSON.stringify({ annualHeartbeat: true, elapsedMs: Date.now() - startedAt, verified: next.verified, pending: next.pending, progressValue: next.progressValue, progressText: next.progressText, atmosphereUnavailableDates: next.atmosphereUnavailableDates.map(item => item.date) }));
    }
    state = next;
  }

  report.terminal = state;
  assert(state.engines.length <= 1 && (state.engines.length === 0 || state.engines[0] === ENGINE), `Annual engine drift: ${JSON.stringify(state.engines)}`);
  assert(state.exportCsvEnabled === true, 'Annual CSV export did not enable at terminal state');
  assert(report.consoleErrors.length === 0, `console errors: ${JSON.stringify(report.consoleErrors)}`);
  assert(report.pageErrors.length === 0, `page errors: ${JSON.stringify(report.pageErrors)}`);
  report.pass = true;
} catch (error) {
  report.error = error?.stack || error?.message || String(error);
  try { report.lastState = await annualState(); } catch {}
  throw error;
} finally {
  writeFileSync(OUTPUT, JSON.stringify(report, null, 2) + '\n');
  await context.close();
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, samples: report.samples, terminal: report.terminal ?? null }, null, 2));

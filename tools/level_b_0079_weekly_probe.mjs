import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const BASE_URL = process.env.DEPLOYMENT_URL;
const APPLICATION_SHA = process.env.APPLICATION_SHA;
const OUTPUT = process.env.WEEKLY_PROBE_OUTPUT || '0079-weekly-probe.json';
const ENGINE = 'level-b-v3-crumey-blackwell-equilibrium';
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
  purpose: 'weekly-worker-heartbeat-diagnosis',
  applicationSha: APPLICATION_SHA,
  deploymentUrl: BASE_URL,
  engine: ENGINE,
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
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
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

async function weeklyState() {
  return page.evaluate(() => {
    const lexical = expression => {
      try { return window.eval(expression); } catch { return null; }
    };
    const rows = typeof weeklyResults !== 'undefined' && Array.isArray(weeklyResults) ? weeklyResults : [];
    const cancel = document.querySelector('#cancelWeekly');
    const calculate = document.querySelector('#calculateWeekly');
    const cancelVisible = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && getComputedStyle(cancel).visibility !== 'hidden' && !cancel.disabled);
    const activeWorker = lexical("typeof activeWeeklyWorker !== 'undefined' ? activeWeeklyWorker : null");
    const version = Number(lexical("typeof weeklyCalculationVersion !== 'undefined' ? weeklyCalculationVersion : NaN"));
    const final = typeof weeklyResultsFinal !== 'undefined' ? weeklyResultsFinal : null;
    const engineOf = row => row?.calculationEngine ?? row?.levelBRunProvenance?.calculationEngine ?? null;
    return {
      at: new Date().toISOString(),
      final,
      length: rows.length,
      pending: rows.filter(row => Boolean(row?.pending)).length,
      provisional: rows.filter(row => Boolean(row?.provisional)).length,
      verified: rows.filter(row => row && !row.pending && row.provisional === false).length,
      engines: [...new Set(rows.map(engineOf).filter(Boolean))],
      progressValue: Number(document.querySelector('#weeklyProgressBar')?.value ?? 0),
      progressText: String(document.querySelector('#weeklyProgressText')?.textContent || '').trim().slice(0, 500),
      calculateDisabled: calculate?.disabled ?? null,
      cancelVisible,
      activeWorker: activeWorker == null ? null : Boolean(activeWorker),
      version: Number.isFinite(version) ? version : null,
      errorText: String(document.querySelector('#error')?.textContent || '').trim().slice(0, 500),
      unexpectedMessage: globalThis.__WEEKLY_LAST_UNEXPECTED_WORKER_MESSAGE__ ?? null,
      terminalDiagnostic: globalThis.__WEEKLY_LAST_TERMINAL_DIAGNOSTIC__ ?? null,
    };
  });
}

function isTerminal(s) {
  return s.final === true && s.length === 7 && s.pending === 0 && s.provisional === 0 && s.verified === 7 && s.calculateDisabled === false && s.cancelVisible === false;
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
  assert(baseline && baseline.calculationEngine === ENGINE, 'equilibrium Three-Star baseline did not bind exact engine');

  const before = await weeklyState();
  report.beforeOpen = before;
  const baselineVersion = Number.isFinite(before.version) ? before.version : -1;
  const weekly = page.locator('#weeklyView');
  await weekly.waitFor({ state: 'visible', timeout: 60000 });
  if (await weekly.evaluate(el => el.open)) {
    await weekly.locator('summary').click();
    await page.waitForFunction(() => document.querySelector('#weeklyView')?.open === false, undefined, { timeout: 10000 });
  }
  await weekly.locator('summary').click();
  await page.waitForFunction(() => document.querySelector('#weeklyView')?.open === true, undefined, { timeout: 10000 });

  let state = await weeklyState();
  const autoDeadline = Date.now() + 15000;
  while (Date.now() < autoDeadline && !(isTerminal(state) || (state.final === false && state.length === 7 && state.pending > 0 && state.activeWorker === true && state.version > baselineVersion))) {
    await page.waitForTimeout(500);
    state = await weeklyState();
  }
  if (!(isTerminal(state) || (state.final === false && state.length === 7 && state.pending > 0 && state.activeWorker === true && state.version > baselineVersion))) {
    const canClick = state.activeWorker !== true && state.cancelVisible === false && state.calculateDisabled === false;
    assert(canClick, `Weekly start ambiguous: ${JSON.stringify(state)}`);
    await page.click('#calculateWeekly');
    await page.waitForTimeout(500);
    state = await weeklyState();
  }

  const startedAt = Date.now();
  let lastHeartbeatAt = startedAt;
  let lastKey = heartbeatKey(state);
  report.samples.push({ elapsedMs: 0, ...state });

  while (!isTerminal(state)) {
    if (isSilentAbort(state)) throw new Error(`Weekly silent abort: ${JSON.stringify(state)}`);
    if (state.errorText) throw new Error(`Weekly application error: ${state.errorText}`);
    const elapsed = Date.now() - startedAt;
    if (elapsed > TOTAL_MS) throw new Error(`Weekly total diagnostic cap exceeded after ${elapsed} ms: ${JSON.stringify(state)}`);
    if (state.activeWorker === true && Date.now() - lastHeartbeatAt > STALL_MS) {
      throw new Error(`Weekly worker stall: no heartbeat for ${Date.now() - lastHeartbeatAt} ms: ${JSON.stringify(state)}`);
    }
    await page.waitForTimeout(POLL_MS);
    const next = await weeklyState();
    const key = heartbeatKey(next);
    if (key !== lastKey) {
      lastHeartbeatAt = Date.now();
      lastKey = key;
      report.samples.push({ elapsedMs: Date.now() - startedAt, ...next });
      console.log(JSON.stringify({ weeklyHeartbeat: true, elapsedMs: Date.now() - startedAt, verified: next.verified, pending: next.pending, progressValue: next.progressValue, progressText: next.progressText }));
    }
    state = next;
  }

  report.terminal = state;
  assert(state.engines.length === 1 && state.engines[0] === ENGINE, `Weekly engine drift: ${JSON.stringify(state.engines)}`);
  assert(report.consoleErrors.length === 0, `console errors: ${JSON.stringify(report.consoleErrors)}`);
  assert(report.pageErrors.length === 0, `page errors: ${JSON.stringify(report.pageErrors)}`);
  report.pass = true;
} catch (error) {
  report.error = error?.stack || error?.message || String(error);
  try { report.lastState = await weeklyState(); } catch {}
  throw error;
} finally {
  writeFileSync(OUTPUT, JSON.stringify(report, null, 2) + '\n');
  await context.close();
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, samples: report.samples, terminal: report.terminal ?? null }, null, 2));

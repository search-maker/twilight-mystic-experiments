import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';

const BASE_URL = process.env.DEPLOYMENT_URL;
const APPLICATION_SHA = process.env.APPLICATION_SHA;
const OUTPUT = process.env.BROWSER_QA_OUTPUT || '0079-browser-qa.json';
if (!BASE_URL || !APPLICATION_SHA) throw new Error('DEPLOYMENT_URL and APPLICATION_SHA are required');

const ENGINES = [
  'legacy',
  'level-b-v3-crumey-blackwell-equilibrium',
  'level-b-v3-crumey-blackwell-transient-experimental',
];
const LEVEL_B_ENGINES = new Set(ENGINES.slice(1));
const EXPECTED_TRANSPORT = 'MYSTIC-STATE-0081-wavelength-resolved-direct-transport';
const EXPECTED_PROMOTION = 'VALIDATED_MYSTIC_STATE_0081_COMPUTATIONAL_REFERENCE_GATE';
const EXPECTED_PROTOCOL = 'aae80c6c958c0d3dabe9e841be50b4fca52e1b5fb717e834d361172bfed00fef';
const EXPECTED_SED = '85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb';
const EXPECTED_LUT = '21eeb51fcc5287ab3bb8cb59cfe0bb0073f34e9ca1b6cc6df988c6eb5043631f';
const EXPECTED_JOHNSON_V = '51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function jsonClone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}
function cloudflareRumConsoleEntry(text, url) {
  return /cloudflareinsights\.com\/cdn-cgi\/rum|\/cdn-cgi\/rum/i.test(`${text || ''} ${url || ''}`);
}

const report = {
  schemaVersion: 2,
  mysticState: 'MYSTIC-STATE-0079',
  applicationSha: APPLICATION_SHA,
  deploymentUrl: BASE_URL,
  browser: 'chromium-playwright',
  location: { name: 'Jerusalem', latitudeDeg: 31.778, longitudeDeg: 35.235, elevationM: 754, timeZone: 'Asia/Jerusalem' },
  date: '2026-08-17',
  exactBindings: { protocolSha256: EXPECTED_PROTOCOL, sedSha256: EXPECTED_SED, lutSha256: EXPECTED_LUT, johnsonVSha256: EXPECTED_JOHNSON_V },
  matrix: [],
  batch: [],
  viewportChecks: [],
  consoleErrors: [],
  ignoredThirdPartyConsoleErrors: [],
  pageErrors: [],
  pass: false,
  claimBoundary: 'deployed-browser-software-integration-only-not-empirical-real-sky-or-human-validation',
};

const browser = await chromium.launch({ headless: true });

async function globalEval(page, expression) {
  return page.evaluate(expr => {
    try { return window.eval(expr); } catch { return null; }
  }, expression);
}

async function waitCalculateReady(page, timeout = 240000) {
  await page.waitForFunction(() => {
    const b = document.querySelector('#calculate');
    return Boolean(
      b
      && !b.disabled
      && b.getAttribute('aria-busy') !== 'true'
      && !b.classList.contains('is-calculating')
    );
  }, undefined, { timeout });
}

async function createPage(viewport) {
  const context = await browser.newContext({ viewport, acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(240000);
  page.setDefaultNavigationTimeout(120000);
  page.on('console', msg => {
    if (msg.type() !== 'error') return;
    const location = msg.location?.() || {};
    const entry = { viewport, text: msg.text(), url: location.url || null, lineNumber: location.lineNumber ?? null, columnNumber: location.columnNumber ?? null };
    if (cloudflareRumConsoleEntry(entry.text, entry.url)) {
      report.ignoredThirdPartyConsoleErrors.push({ ...entry, classification: 'cloudflare-insights-rum-cors' });
    } else {
      report.consoleErrors.push(entry);
    }
  });
  page.on('pageerror', error => report.pageErrors.push({ viewport, text: error?.stack || error?.message || String(error) }));
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { state: 'visible', timeout: 60000 });
  await page.waitForFunction(() => document.querySelector('#calculate') && document.querySelector('#threeStarCalculatorTab'), undefined, { timeout: 60000 });
  await waitCalculateReady(page);
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
  await waitCalculateReady(page);
  return { context, page };
}

async function selectEngine(page, engine) {
  await waitCalculateReady(page);
  await page.selectOption('#visibilityEngineMode', engine);
  await waitCalculateReady(page);
  const state = await page.evaluate(() => ({
    value: document.querySelector('#visibilityEngineMode')?.value,
    globalValue: globalThis.__STAR_VISIBILITY_ENGINE_MODE__,
    stored: (() => { try { return localStorage.getItem('starVisibilitySitewideEnginePreviewV1'); } catch { return null; } })(),
    note: document.querySelector('#visibilityEngineModeNote')?.textContent || '',
  }));
  assert(state.value === engine, `engine selector did not retain ${engine}`);
  assert(state.globalValue === engine, `global engine did not bind ${engine}`);
  assert(state.stored === engine, `localStorage engine did not bind ${engine}`);
  assert(/MYSTIC-STATE-0081/.test(state.note), 'Preview note does not disclose MYSTIC-STATE-0081');
  assert(/not empirically or human validated|אינו מאומת אמפירית או בבני-אדם/.test(state.note), 'Preview note lost empirical/human-validation boundary');
  return state;
}

async function chooseFeature(page, feature) {
  await waitCalculateReady(page);
  const id = feature === 'three-star' ? '#threeStarCalculatorTab' : '#standardCalculatorTab';
  await page.click(id);
  await page.waitForFunction(expected => document.querySelector('#calculatorFeature')?.value === expected, feature, { timeout: 60000 });
  await waitCalculateReady(page);
  assert(await page.$eval('#calculatorFeature', el => el.value) === feature, `calculatorFeature did not become ${feature}`);
}

async function waitDailyDone(page) {
  await page.waitForTimeout(150);
  await waitCalculateReady(page);
}

async function calculateDaily(page, engine, feature) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, feature);
  await waitCalculateReady(page);
  await page.click('#calculate');
  await waitDailyDone(page);
  const error = await page.evaluate(() => {
    const el = document.querySelector('#error');
    return el && (el.classList.contains('show') || !el.hidden) ? (el.textContent || '').trim() : '';
  });
  assert(!error, `${engine}/${feature} produced application error: ${error}`);

  const state = {
    metadata: jsonClone(await globalEval(page, 'lastRunMetadata')),
    rows: jsonClone(await globalEval(page, 'rows')),
    threeStar: jsonClone(await globalEval(page, 'threeStarResultData')),
    calculatorFeature: await page.$eval('#calculatorFeature', el => el.value),
    engineValue: await page.$eval('#visibilityEngineMode', el => el.value),
  };
  assert(state.calculatorFeature === feature, `${engine}/${feature} feature changed during calculation`);
  assert(state.engineValue === engine, `${engine}/${feature} engine changed during calculation`);

  if (feature === 'standard') {
    assert(Array.isArray(state.rows) && state.rows.length > 0, `${engine}/standard produced no rows`);
    if (LEVEL_B_ENGINES.has(engine)) {
      assert(state.rows.every(row => row?.calculationEngine === engine), `${engine}/standard contains silent non-Level-B rows`);
      assert(state.rows.every(row => row?.levelBLegacyVisibilityDiscarded === true), `${engine}/standard did not discard Legacy visibility scaffold`);
      assert(state.rows.every(row => row?.levelBStellarTransport === EXPECTED_TRANSPORT), `${engine}/standard transport provenance drift`);
      assert(state.rows.every(row => row?.levelBStellarTransportPromotionStatus === EXPECTED_PROMOTION), `${engine}/standard promotion provenance drift`);
      assert(state.metadata?.levelBStellarTransport === EXPECTED_TRANSPORT, `${engine}/standard run metadata transport drift`);
      assert(state.metadata?.levelBStellarTransportPromotionStatus === EXPECTED_PROMOTION, `${engine}/standard run metadata promotion drift`);
      assert(state.metadata?.levelBStellarTransportProtocolSha256 === EXPECTED_PROTOCOL, `${engine}/standard protocol binding drift`);
      assert(state.metadata?.levelBStellarTransportSedSha256 === EXPECTED_SED, `${engine}/standard SED binding drift`);
      assert(state.metadata?.levelBStellarTransportLutSha256 === EXPECTED_LUT, `${engine}/standard LUT binding drift`);
      assert(state.metadata?.levelBRunProvenance?.productionAuthorized === false, `${engine}/standard falsely claims production authorization`);
      assert(state.metadata?.levelBRunProvenance?.measuredRealSkyValidated === false, `${engine}/standard falsely claims measured-real-sky validation`);
      assert(state.metadata?.levelBRunProvenance?.empiricalHumanValidationComplete === false, `${engine}/standard falsely claims empirical human validation`);
    }
  } else {
    assert(state.threeStar && typeof state.threeStar === 'object', `${engine}/three-star produced no result object`);
    if (LEVEL_B_ENGINES.has(engine)) {
      assert(state.threeStar.calculationEngine === engine, `${engine}/three-star silently changed engine`);
      assert(state.threeStar.planetsCountTowardThreeStars === false, `${engine}/three-star unexpectedly counts planets`);
      assert(state.threeStar.levelBRunProvenance?.stellarTransport === EXPECTED_TRANSPORT, `${engine}/three-star transport provenance drift`);
      assert(state.threeStar.levelBRunProvenance?.stellarTransportPromotionStatus === EXPECTED_PROMOTION, `${engine}/three-star promotion provenance drift`);
      assert(state.threeStar.levelBRunProvenance?.stellarTransportProtocolSha256 === EXPECTED_PROTOCOL, `${engine}/three-star protocol binding drift`);
      assert(state.threeStar.levelBRunProvenance?.stellarTransportSedSha256 === EXPECTED_SED, `${engine}/three-star SED binding drift`);
      assert(state.threeStar.levelBRunProvenance?.stellarTransportLutSha256 === EXPECTED_LUT, `${engine}/three-star LUT binding drift`);
      assert(state.threeStar.levelBRunProvenance?.productionAuthorized === false, `${engine}/three-star falsely claims production authorization`);
      assert(state.threeStar.levelBRunProvenance?.measuredRealSkyValidated === false, `${engine}/three-star falsely claims measured-real-sky validation`);
      assert(state.threeStar.levelBRunProvenance?.empiricalHumanValidationComplete === false, `${engine}/three-star falsely claims empirical human validation`);
    }
  }

  report.matrix.push({ engine, feature, rowCount: Array.isArray(state.rows) ? state.rows.length : null, threeStarFound: state.threeStar?.found ?? null, levelBReason: state.threeStar?.reason ?? null });
  return state;
}

async function waitGlobal(page, expression, timeout = 300000) {
  await page.waitForFunction(expr => {
    try { return Boolean(window.eval(expr)); } catch { return false; }
  }, expression, { timeout });
}

async function runWeekly(page, engine) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, 'three-star');
  await page.evaluate(() => { const el = document.querySelector('#weeklyView'); if (el && !el.open) el.querySelector('summary')?.click(); });
  await waitGlobal(page, 'weeklyResultsFinal === true && Array.isArray(weeklyResults) && weeklyResults.length === 7');
  const rows = jsonClone(await globalEval(page, 'weeklyResults'));
  assert(rows.length === 7 && rows.every(row => !row?.pending), 'weekly worker did not produce 7 terminal dates');
  if (LEVEL_B_ENGINES.has(engine)) {
    assert(rows.every(row => row?.calculationEngine === engine || row?.levelBRunProvenance?.calculationEngine === engine), `${engine}/weekly silently changed engine`);
  }
  report.batch.push({ engine, feature: 'weekly', count: rows.length });
}

async function runAnnualMonthAndExport(page, engine) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, 'three-star');
  await page.evaluate(() => {
    const details = document.querySelector('#annualView'); if (details && !details.open) details.querySelector('summary')?.click();
    const set = (id, value) => { const el = document.getElementById(id); if (!el) return; el.value = value; el.dispatchEvent(new Event('change', { bubbles: true })); };
    set('annualCalendar', 'gregorian-month');
    set('annualMonth', '2026-08');
    set('annualCadence', 'weekly');
  });
  await page.click('#calculateAnnual');
  await waitGlobal(page, 'annualResultsFinal === true && Array.isArray(annualResults) && annualResults.length >= 4', 360000);
  const annual = jsonClone(await globalEval(page, 'annualResults'));
  assert(annual.length >= 4 && annual.length <= 6, `annual monthly weekly cadence unexpected count ${annual.length}`);
  if (LEVEL_B_ENGINES.has(engine)) {
    assert(annual.every(row => row?.calculationEngine === engine || row?.levelBRunProvenance?.calculationEngine === engine), `${engine}/annual silently changed engine`);
  }
  assert(await page.isEnabled('#exportAnnualCsv'), 'annual CSV export did not enable');
  const [download] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), page.click('#exportAnnualCsv')]);
  const path = await download.path();
  assert(path, 'annual CSV download has no path');
  const csv = readFileSync(path, 'utf8');
  if (LEVEL_B_ENGINES.has(engine)) {
    assert(csv.includes('MYSTIC-STATE-0081') || csv.includes(EXPECTED_TRANSPORT), 'annual CSV lost Level-B stellar provenance');
  }
  report.batch.push({ engine, feature: 'annual-month-weekly+csv-export', count: annual.length, csvBytes: Buffer.byteLength(csv) });
}

async function runComparison(page, engine) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, 'three-star');
  await page.evaluate(() => {
    const details = document.querySelector('#comparisonView'); if (details && !details.open) details.querySelector('summary')?.click();
    const scope = document.querySelector('#comparisonScope'); if (scope) { scope.value = 'day'; scope.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await page.click('#calculateComparison');
  await waitGlobal(page, 'comparisonResultsFinal === true && Array.isArray(comparisonResultsA) && comparisonResultsA.length === 1 && Array.isArray(comparisonResultsB) && comparisonResultsB.length === 1', 360000);
  const a = jsonClone(await globalEval(page, 'comparisonResultsA'));
  const b = jsonClone(await globalEval(page, 'comparisonResultsB'));
  assert(a.length === 1 && b.length === 1, 'comparison day did not produce both scenarios');
  if (LEVEL_B_ENGINES.has(engine)) {
    assert([...a, ...b].every(row => row?.calculationEngine === engine || row?.levelBRunProvenance?.calculationEngine === engine), `${engine}/comparison silently changed engine`);
  }
  report.batch.push({ engine, feature: 'comparison-day', countA: a.length, countB: b.length });
}

async function runSkyMap(page, engine) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, 'three-star');
  let result = jsonClone(await globalEval(page, 'threeStarResultData'));
  if (!result || result.calculationEngine !== engine) result = (await calculateDaily(page, engine, 'three-star')).threeStar;
  const detailsExists = await page.locator('#threeStarSkyMapView').count();
  assert(detailsExists === 1, 'sky-map view missing');
  await page.evaluate(() => {
    const el = document.querySelector('#threeStarSkyMapView'); if (el && !el.open) el.querySelector('summary')?.click();
  });
  await page.waitForTimeout(500);
  const skyMap = jsonClone(await globalEval(page, 'threeStarSkyMapData'));
  assert(skyMap && typeof skyMap === 'object', 'sky-map route produced no state object');
  if (LEVEL_B_ENGINES.has(engine) && skyMap.levelBRunProvenance) {
    assert(skyMap.levelBRunProvenance.calculationEngine === engine, `${engine}/sky-map silently changed engine`);
    assert(skyMap.levelBRunProvenance.stellarTransport === EXPECTED_TRANSPORT, `${engine}/sky-map transport provenance drift`);
  }
  report.batch.push({ engine, feature: 'sky-map', found: skyMap.found ?? null, frameCount: Array.isArray(skyMap.frames) ? skyMap.frames.length : 0, reason: skyMap.reason ?? null });
}

async function assertViewport(page, viewport, label) {
  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const selector = document.querySelector('#visibilityEngineModeField');
    const controls = document.querySelector('.level-b-sitewide-controls-host');
    const box = el => el ? ({ left: el.getBoundingClientRect().left, right: el.getBoundingClientRect().right, width: el.getBoundingClientRect().width }) : null;
    return { clientWidth: root.clientWidth, scrollWidth: root.scrollWidth, selector: box(selector), controls: box(controls) };
  });
  assert(metrics.scrollWidth <= metrics.clientWidth + 2, `${label} horizontal document overflow ${metrics.scrollWidth}>${metrics.clientWidth}`);
  for (const [name, box] of Object.entries({ selector: metrics.selector, controls: metrics.controls })) {
    if (!box) continue;
    assert(box.left >= -2 && box.right <= metrics.clientWidth + 2, `${label} ${name} escapes viewport`);
  }
  report.viewportChecks.push({ label, viewport, ...metrics });
}

try {
  const wide = await createPage({ width: 1440, height: 1000 });
  await assertViewport(wide.page, { width: 1440, height: 1000 }, 'wide-initial');

  for (const engine of ENGINES) {
    await calculateDaily(wide.page, engine, 'standard');
    await calculateDaily(wide.page, engine, 'three-star');
  }
  await runComparison(wide.page, 'legacy');
  await runWeekly(wide.page, 'level-b-v3-crumey-blackwell-equilibrium');
  await runSkyMap(wide.page, 'level-b-v3-crumey-blackwell-equilibrium');
  await runAnnualMonthAndExport(wide.page, 'level-b-v3-crumey-blackwell-transient-experimental');
  await assertViewport(wide.page, { width: 1440, height: 1000 }, 'wide-after-dynamic-results');
  await wide.context.close();

  const narrow = await createPage({ width: 375, height: 812 });
  await assertViewport(narrow.page, { width: 375, height: 812 }, 'narrow-initial');
  await calculateDaily(narrow.page, 'level-b-v3-crumey-blackwell-transient-experimental', 'three-star');
  await assertViewport(narrow.page, { width: 375, height: 812 }, 'narrow-after-three-star');
  await narrow.context.close();

  assert(report.pageErrors.length === 0, `page errors observed: ${JSON.stringify(report.pageErrors)}`);
  assert(report.consoleErrors.length === 0, `unexpected console errors observed: ${JSON.stringify(report.consoleErrors)}`);
  report.pass = true;
} finally {
  await browser.close();
  writeFileSync(OUTPUT, JSON.stringify(report, null, 2) + '\n');
}

console.log(JSON.stringify({ pass: report.pass, matrix: report.matrix, batch: report.batch, viewportChecks: report.viewportChecks, ignoredThirdPartyConsoleErrors: report.ignoredThirdPartyConsoleErrors }, null, 2));

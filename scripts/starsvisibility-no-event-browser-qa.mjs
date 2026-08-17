import { chromium } from 'playwright';
import fs from 'node:fs';

const targetUrl = process.env.TARGET_URL;
const ENGINE = 'level-b-v3-crumey-blackwell-equilibrium';
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const diagnostics = [];
let failed = false;
const browser = await chromium.launch({ headless: true });

async function setValueSilently(page, selector, value) {
  await page.locator(selector).evaluate((el, nextValue) => {
    const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype
      : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(el, String(nextValue));
    else el.value = String(nextValue);
  }, value);
}

async function resetCalculationState(page) {
  const reset = await page.evaluate(() => {
    try {
      return globalThis.eval(`
        disposeReusableCalculationWorker();
        activeCalculationWorker = null;
        calculationResultsFinal = false;
        threeStarResultData = null;
        lastRunMetadata = {};
        ({ workerEnabled, calculationResultsFinal })
      `);
    } catch (error) {
      return { error: String(error?.stack || error) };
    }
  });
  if (reset?.error) throw new Error(`Could not reset calculation state: ${reset.error}`);
  return reset;
}

async function installFeatureAudit(page) {
  await page.evaluate(() => {
    const feature = document.querySelector('#calculatorFeature');
    if (!feature) throw new Error('#calculatorFeature missing');
    const proto = feature instanceof HTMLInputElement ? HTMLInputElement.prototype
      : feature instanceof HTMLSelectElement ? HTMLSelectElement.prototype
      : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (!descriptor?.get || !descriptor?.set) throw new Error('calculatorFeature value descriptor unavailable');
    globalThis.__noEventQaFeatureHistory = [String(descriptor.get.call(feature))];
    Object.defineProperty(feature, 'value', {
      configurable: true,
      enumerable: descriptor.enumerable,
      get() { return descriptor.get.call(this); },
      set(nextValue) {
        const value = String(nextValue);
        globalThis.__noEventQaFeatureHistory.push(value);
        descriptor.set.call(this, value);
      },
    });
  });
}

async function waitForFinalLevelBResult(page) {
  await page.waitForFunction(expectedEngine => {
    try {
      const state = globalThis.eval('({ final: calculationResultsFinal, result: threeStarResultData, metadata: lastRunMetadata })');
      const engine = state.result?.calculationEngine
        ?? state.metadata?.calculationEngine
        ?? state.metadata?.levelBRunProvenance?.calculationEngine
        ?? null;
      return state.final === true && state.result !== null && engine === expectedEngine;
    } catch {
      return false;
    }
  }, ENGINE, { timeout: 300000 });
}

const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
const page = await context.newPage();
const pageErrors = [];
const consoleErrors = [];
const failedRequests = [];
page.on('pageerror', err => pageErrors.push(String(err?.stack || err)));
page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
page.on('requestfailed', req => failedRequests.push({ url: req.url(), error: req.failure()?.errorText || 'unknown' }));

const diag = {
  viewport: { name: 'no-event-desktop', width: 1440, height: 1000 },
  httpStatus: null,
  reset: null,
  inputs: null,
  featureHistory: [],
  finalResult: null,
  candidateDiagnosticLine: null,
  horizontalOverflowPx: null,
  mobileHorizontalOverflowPx: null,
  pageErrors,
  consoleErrors,
  failedRequests,
  assertions: [],
};
const assert = (condition, message) => {
  diag.assertions.push({ ok: Boolean(condition), message });
  if (!condition) failed = true;
};

try {
  const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  diag.httpStatus = response?.status() ?? null;
  assert(Boolean(response?.ok()), `Deployment returns successful HTTP status (got ${diag.httpStatus})`);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});

  for (const selector of ['#calculatorFeature','#threeStarMagnitudeBasis','#threeStarMagnitudeThreshold','#threeStarCount','#minAlt','#visibilityEngineMode','#calculate']) {
    await page.locator(selector).waitFor({ state: 'attached', timeout: 20000 });
  }

  diag.reset = await resetCalculationState(page);
  await setValueSilently(page, '#calculatorFeature', 'three-star');
  await setValueSilently(page, '#threeStarMagnitudeBasis', 'effective');
  await setValueSilently(page, '#threeStarMagnitudeThreshold', '1.7');
  await setValueSilently(page, '#threeStarCount', '3');
  await setValueSilently(page, '#minAlt', '89');
  await setValueSilently(page, '#visibilityEngineMode', ENGINE);

  diag.inputs = await page.evaluate(() => ({
    feature: document.querySelector('#calculatorFeature')?.value ?? null,
    basis: document.querySelector('#threeStarMagnitudeBasis')?.value ?? null,
    threshold: document.querySelector('#threeStarMagnitudeThreshold')?.value ?? null,
    count: document.querySelector('#threeStarCount')?.value ?? null,
    minAlt: document.querySelector('#minAlt')?.value ?? null,
    minAltValid: document.querySelector('#minAlt')?.checkValidity?.() ?? null,
    engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
  }));
  assert(diag.inputs.feature === 'three-star', `Three-Star feature is selected (got ${diag.inputs.feature})`);
  assert(diag.inputs.basis === 'effective', `Effective magnitude basis is selected (got ${diag.inputs.basis})`);
  assert(Number(diag.inputs.threshold) === 1.7, `Magnitude threshold is 1.7 (got ${diag.inputs.threshold})`);
  assert(diag.inputs.count === '3', `Three-Star required count is 3 (got ${diag.inputs.count})`);
  assert(Number(diag.inputs.minAlt) === 89, `Minimum star altitude is 89 degrees (got ${diag.inputs.minAlt})`);
  assert(diag.inputs.minAltValid !== false, '89-degree minimum altitude passes browser validity');
  assert(diag.inputs.engine === ENGINE, `Level-B equilibrium engine is selected (got ${diag.inputs.engine})`);

  await installFeatureAudit(page);
  await page.locator('#calculate').click();
  await waitForFinalLevelBResult(page);

  diag.featureHistory = await page.evaluate(() => [...(globalThis.__noEventQaFeatureHistory || [])]);
  const finalState = await page.evaluate(() => globalThis.eval(`(() => ({
    final: calculationResultsFinal,
    result: threeStarResultData ? JSON.parse(JSON.stringify(threeStarResultData)) : null,
    metadata: lastRunMetadata ? JSON.parse(JSON.stringify(lastRunMetadata)) : null
  }))()`));
  diag.finalResult = finalState.result;

  assert(finalState.final === true, 'Calculation is final');
  assert(finalState.result?.calculationEngine === ENGINE, `Final Three-Star result is Level-B equilibrium (got ${finalState.result?.calculationEngine})`);
  assert(finalState.result?.found === false, `89-degree fixture produces no event (found=${finalState.result?.found})`);
  assert(finalState.result?.time === null, `No-event Level-B result exposes time=null (got ${finalState.result?.time})`);
  assert(finalState.result?.eventTime === null, `No-event Level-B result exposes eventTime=null (got ${finalState.result?.eventTime})`);
  assert(Number(finalState.result?.candidateCount) > 0, `No-event diagnostics retain a nonzero candidate count (got ${finalState.result?.candidateCount})`);
  assert(Number(finalState.result?.eligibleCandidateCount) > 0, `No-event diagnostics retain nonzero eligible candidates (got ${finalState.result?.eligibleCandidateCount})`);
  assert(Number(finalState.result?.pointwiseCandidateCount) > 0, `No-event diagnostics retain nonzero pointwise candidates (got ${finalState.result?.pointwiseCandidateCount})`);
  assert(diag.featureHistory.every(value => value === 'three-star'),
    `Three-Star never routes through Standard on the page (history: ${JSON.stringify(diag.featureHistory)})`);

  const body = await page.locator('body').innerText();
  const lines = body.split(/\n+/).map(line => line.trim()).filter(Boolean);
  const candidateLine = lines.find(line => /(?:candidate|מועמד)/i.test(line) && /(?:scan|נסרק)/i.test(line))
    || lines.find(line => /(?:candidate|מועמד)/i.test(line) && /\d+/.test(line));
  diag.candidateDiagnosticLine = candidateLine || null;
  assert(!/Three-star time:\s*\d{1,2}:\d{2}\s*[·-]\s*Verified/i.test(body), '89-degree fixture does not render a verified event');
  assert(Boolean(candidateLine), 'No-event UI renders candidate diagnostics');
  if (candidateLine) {
    const match = candidateLine.match(/(\d+)/);
    assert(match && Number(match[1]) > 0, `Rendered no-event candidate count is nonzero (${candidateLine})`);
  }

  diag.horizontalOverflowPx = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
  assert(diag.horizontalOverflowPx <= 1, `No desktop horizontal overflow (got ${diag.horizontalOverflowPx}px)`);
  await page.screenshot({ path: 'qa-artifacts/no-event-desktop.png', fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(150);
  diag.mobileHorizontalOverflowPx = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
  assert(diag.mobileHorizontalOverflowPx <= 1, `No mobile horizontal overflow (got ${diag.mobileHorizontalOverflowPx}px)`);
  await page.screenshot({ path: 'qa-artifacts/no-event-mobile-390.png', fullPage: true });

  assert(pageErrors.length === 0, `No uncaught page errors (got ${pageErrors.length})`);
  assert(consoleErrors.length === 0, `No console errors (got ${consoleErrors.length})`);
  assert(failedRequests.length === 0, `No failed network requests (got ${failedRequests.length})`);
} catch (error) {
  failed = true;
  diag.fatalError = String(error?.stack || error);
  try { await page.screenshot({ path: 'qa-artifacts/no-event-failure.png', fullPage: true }); } catch {}
} finally {
  diagnostics.push(diag);
  await context.close();
  await browser.close();
}

fs.mkdirSync('qa-artifacts', { recursive: true });
fs.writeFileSync('qa-artifacts/no-event-diagnostics.json', JSON.stringify(diagnostics, null, 2));
console.log(JSON.stringify(diagnostics, null, 2));
if (failed) process.exitCode = 1;

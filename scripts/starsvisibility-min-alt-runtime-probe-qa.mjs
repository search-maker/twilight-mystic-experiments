import { chromium } from 'playwright';

const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
const page = await context.newPage();

async function setValueSilently(selector, value) {
  await page.locator(selector).evaluate((el, nextValue) => {
    const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype
      : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(el, String(nextValue));
    else el.value = String(nextValue);
  }, value);
}

try {
  const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  if (!response?.ok()) throw new Error(`Preview returned HTTP ${response?.status()}`);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});

  await page.locator('#visibilityEngineMode').waitFor({ state: 'attached', timeout: 20000 });
  const disable = await page.evaluate(() => {
    try {
      return globalThis.eval('workerEnabled = false; ({ workerEnabled })');
    } catch (error) {
      return { error: String(error?.stack || error) };
    }
  });
  if (disable?.error) throw new Error(`Could not disable worker for diagnostic: ${disable.error}`);

  // Silent setters are intentional: several legacy Three-Star controls auto-run
  // calculate() on change. The diagnostic must have exactly one calculation,
  // after all Level-B inputs have reached their final values.
  await setValueSilently('#calculatorFeature', 'three-star');
  await setValueSilently('#threeStarMagnitudeBasis', 'effective');
  await setValueSilently('#threeStarMagnitudeThreshold', '1.7');
  await setValueSilently('#threeStarCount', '3');
  await setValueSilently('#minAlt', '89');
  await setValueSilently('#visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium');

  const inputsBefore = await page.evaluate(() => ({
    feature: document.querySelector('#calculatorFeature')?.value ?? null,
    basis: document.querySelector('#threeStarMagnitudeBasis')?.value ?? null,
    threshold: document.querySelector('#threeStarMagnitudeThreshold')?.value ?? null,
    count: document.querySelector('#threeStarCount')?.value ?? null,
    minAlt: document.querySelector('#minAlt')?.value ?? null,
    engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
    engineFromRuntime: globalThis.eval('__levelBSitewideEngineMode()'),
  }));

  const calculate = page.locator('#calculate');
  await calculate.waitFor({ state: 'visible', timeout: 10000 });
  const clickedControl = await calculate.evaluate(el => ({
    id: el.id,
    tag: el.tagName,
    text: (el.textContent || '').trim(),
    value: 'value' in el ? el.value : null,
  }));
  await calculate.click();

  await page.waitForFunction(() => {
    try {
      return globalThis.eval('calculationResultsFinal === true && threeStarResultData !== null');
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.waitForTimeout(250);

  const runtime = await page.evaluate(() => {
    let result = null;
    let metadata = null;
    try {
      if (typeof threeStarResultData !== 'undefined' && threeStarResultData) result = JSON.parse(JSON.stringify(threeStarResultData));
      if (typeof lastRunMetadata !== 'undefined' && lastRunMetadata) metadata = JSON.parse(JSON.stringify(lastRunMetadata));
    } catch (error) {
      result = { readError: String(error?.message || error) };
    }
    return {
      result,
      metadata,
      resultCard: {
        title: document.querySelector('#threeStarResultTitle')?.textContent ?? null,
        empty: document.querySelector('#threeStarEmpty')?.textContent ?? null,
        cardHidden: document.querySelector('#threeStarResult')?.hidden ?? null,
      },
      inputsAfter: {
        feature: document.querySelector('#calculatorFeature')?.value ?? null,
        minAlt: document.querySelector('#minAlt')?.value ?? null,
        engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
      },
    };
  });

  const diagnostic = { url: page.url(), disable, clickedControl, inputsBefore, ...runtime };
  console.log(JSON.stringify(diagnostic, null, 2));

  const calculationEngine = runtime.result?.calculationEngine ?? runtime.metadata?.calculationEngine ?? runtime.metadata?.levelBRunProvenance?.calculationEngine;
  if (calculationEngine !== 'level-b-v3-crumey-blackwell-equilibrium') {
    throw new Error(`Main-thread diagnostic did not run Level-B equilibrium: ${calculationEngine}`);
  }
  if (runtime.result?.found !== false) {
    throw new Error(`Main-thread Level-B should reject the 89-degree fixture, got found=${runtime.result?.found}`);
  }
  if (!(Number(runtime.result?.candidateCount) > 0)) {
    throw new Error(`Main-thread Level-B no-event diagnostics should retain candidates, got ${runtime.result?.candidateCount}`);
  }
} finally {
  await context.close();
  await browser.close();
}

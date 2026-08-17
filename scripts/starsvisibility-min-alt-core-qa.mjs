import { chromium } from 'playwright';

const targetUrl = process.env.TARGET_URL || 'https://preview-level-b-v3-sitewide-9a29.starsvisibility.pages.dev/';
const ENGINE = 'level-b-v3-crumey-blackwell-equilibrium';
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
  for (const selector of ['#calculatorFeature','#threeStarMagnitudeBasis','#threeStarMagnitudeThreshold','#threeStarCount','#minAlt','#visibilityEngineMode','#calculate']) {
    await page.locator(selector).waitFor({ state: 'attached', timeout: 20000 });
  }

  const reset = await page.evaluate(() => globalThis.eval(`
    disposeReusableCalculationWorker();
    activeCalculationWorker = null;
    calculationResultsFinal = false;
    threeStarResultData = null;
    lastRunMetadata = {};
    ({ workerEnabled, calculationResultsFinal })
  `));

  await setValueSilently('#calculatorFeature', 'three-star');
  await setValueSilently('#threeStarMagnitudeBasis', 'effective');
  await setValueSilently('#threeStarMagnitudeThreshold', '1.7');
  await setValueSilently('#threeStarCount', '3');
  await setValueSilently('#minAlt', '89');
  await setValueSilently('#visibilityEngineMode', ENGINE);

  const inputs = await page.evaluate(() => ({
    feature: document.querySelector('#calculatorFeature')?.value ?? null,
    basis: document.querySelector('#threeStarMagnitudeBasis')?.value ?? null,
    threshold: document.querySelector('#threeStarMagnitudeThreshold')?.value ?? null,
    count: document.querySelector('#threeStarCount')?.value ?? null,
    minAlt: document.querySelector('#minAlt')?.value ?? null,
    engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
  }));
  if (inputs.feature !== 'three-star' || inputs.basis !== 'effective' || Number(inputs.threshold) !== 1.7 || inputs.count !== '3' || Number(inputs.minAlt) !== 89 || inputs.engine !== ENGINE) {
    throw new Error(`Unexpected fixture inputs: ${JSON.stringify(inputs)}`);
  }

  const startedAt = Date.now();
  await page.locator('#calculate').click();
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
  }, ENGINE, { timeout: 420000 });

  const final = await page.evaluate(() => globalThis.eval(`(() => ({
    result: threeStarResultData ? JSON.parse(JSON.stringify(threeStarResultData)) : null,
    metadata: lastRunMetadata ? JSON.parse(JSON.stringify(lastRunMetadata)) : null,
    final: calculationResultsFinal
  }))()`));
  const elapsedMs = Date.now() - startedAt;
  const diagnostic = { url: page.url(), reset, inputs, elapsedMs, ...final };
  console.log(JSON.stringify(diagnostic, null, 2));

  if (final.result?.calculationEngine !== ENGINE) throw new Error(`Final result engine is ${final.result?.calculationEngine}`);
  if (final.result?.found !== false) throw new Error(`89-degree final Level-B result must be found=false, got ${final.result?.found}`);
  if (!(Number(final.result?.candidateCount) > 0)) throw new Error(`candidateCount must be nonzero, got ${final.result?.candidateCount}`);
  if (!(Number(final.result?.eligibleCandidateCount) > 0)) throw new Error(`eligibleCandidateCount must be nonzero, got ${final.result?.eligibleCandidateCount}`);
  if (!(Number(final.result?.pointwiseCandidateCount) > 0)) throw new Error(`pointwiseCandidateCount must be nonzero, got ${final.result?.pointwiseCandidateCount}`);
  if (!Array.isArray(final.result?.stars) || final.result.stars.length !== 0) throw new Error('No-event result must expose an empty stars array');
} finally {
  await context.close();
  await browser.close();
}

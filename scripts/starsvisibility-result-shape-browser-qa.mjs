import { chromium } from 'playwright';

const targetUrl = process.env.TARGET_URL || 'https://preview-level-b-v3-sitewide-9a29.starsvisibility.pages.dev/';
const ENGINE = 'level-b-v3-crumey-blackwell-equilibrium';
const htmlResponse = await fetch(targetUrl, { redirect: 'follow' });
if (!htmlResponse.ok) throw new Error(`Preview HTML returned HTTP ${htmlResponse.status}`);
let html = await htmlResponse.text();
if (!html.includes('LEVEL-B-THREE-STAR-MIN-ALTITUDE-V1')) throw new Error('Deployed Preview does not contain minimum-altitude V1 patch');

const failureAnchor = '          date: input.date, timeZone: input.timeZone, eventTime: null, sunsetTime: sunsetMs, requiredCount,';
const failureReplacement = '// LEVEL-B-THREE-STAR-RESULT-TIME-PARITY-V1\n          date: input.date, timeZone: input.timeZone, time: null, eventTime: null, sunsetTime: sunsetMs, requiredCount,';
const successAnchor = '        eventTime: event.eventTimeMs, sunsetTime: sunsetMs, minutesAfterSunset: (event.eventTimeMs - sunsetMs) / 60000,';
const successReplacement = '        time: event.eventTimeMs, eventTime: event.eventTimeMs, sunsetTime: sunsetMs, minutesAfterSunset: (event.eventTimeMs - sunsetMs) / 60000,';
const count = (source, needle) => source.split(needle).length - 1;
if (count(html, failureAnchor) !== 1 || count(html, successAnchor) !== 1) {
  throw new Error(`Unexpected result-shape anchors: failure=${count(html, failureAnchor)} success=${count(html, successAnchor)}`);
}
html = html.replace(failureAnchor, failureReplacement).replace(successAnchor, successReplacement);

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
const page = await context.newPage();
await page.route(targetUrl, async route => {
  await route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
});

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
  if (!response?.ok()) throw new Error(`Synthetic document returned HTTP ${response?.status()}`);
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
  await setValueSilently('#minAlt', '3');
  await setValueSilently('#visibilityEngineMode', ENGINE);

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
  const body = await page.locator('body').innerText();
  const overflowDesktop = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
  await page.screenshot({ path: 'result-shape-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(150);
  const overflowMobile = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
  await page.screenshot({ path: 'result-shape-mobile-390.png', fullPage: true });

  const diagnostic = {
    url: page.url(),
    reset,
    elapsedMs: Date.now() - startedAt,
    result: final.result,
    overflowDesktop,
    overflowMobile,
    renderedVerifiedTime: /Three-star time:\s*\d{1,2}:\d{2}\s*[·-]\s*Verified/i.test(body),
  };
  console.log(JSON.stringify(diagnostic, null, 2));

  if (final.result?.calculationEngine !== ENGINE) throw new Error(`Final result engine is ${final.result?.calculationEngine}`);
  if (final.result?.found !== true) throw new Error(`Default Level-B fixture must return found=true, got ${final.result?.found}`);
  if (!Number.isFinite(final.result?.time)) throw new Error(`Renderer-compatible time is not finite: ${final.result?.time}`);
  if (final.result.time !== final.result.eventTime) throw new Error(`time/eventTime mismatch: ${final.result.time} vs ${final.result.eventTime}`);
  if (!diagnostic.renderedVerifiedTime) throw new Error('Renderer did not show the verified Three-Star time after time-parity patch');
  if (!Array.isArray(final.result?.stars) || final.result.stars.length < 3) throw new Error('Final result contains fewer than three stars');
  if (final.result.stars.some(star => Number(star.apparentAltitude) < 3 - 1e-8)) throw new Error('Selected star violates the 3-degree minimum altitude');
  if (overflowDesktop > 1 || overflowMobile > 1) throw new Error(`Horizontal overflow desktop=${overflowDesktop} mobile=${overflowMobile}`);
} finally {
  await context.close();
  await browser.close();
}

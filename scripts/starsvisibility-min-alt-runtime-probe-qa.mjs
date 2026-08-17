import { chromium } from 'playwright';

const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
const page = await context.newPage();

async function setInputValue(selector, value) {
  await page.locator(selector).evaluate((el, nextValue) => {
    const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype
      : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(el, String(nextValue));
    else el.value = String(nextValue);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

try {
  const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  if (!response?.ok()) throw new Error(`Preview returned HTTP ${response?.status()}`);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});

  await page.locator('#calculatorFeature').waitFor({ state: 'attached', timeout: 20000 });
  await setInputValue('#calculatorFeature', 'three-star');
  await setInputValue('#threeStarMagnitudeBasis', 'effective');
  await setInputValue('#threeStarMagnitudeThreshold', '1.7');
  await setInputValue('#threeStarCount', '3');
  await setInputValue('#minAlt', '89');
  await setInputValue('#visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium');

  const inputsBefore = await page.evaluate(() => ({
    feature: document.querySelector('#calculatorFeature')?.value ?? null,
    basis: document.querySelector('#threeStarMagnitudeBasis')?.value ?? null,
    threshold: document.querySelector('#threeStarMagnitudeThreshold')?.value ?? null,
    count: document.querySelector('#threeStarCount')?.value ?? null,
    minAlt: document.querySelector('#minAlt')?.value ?? null,
    engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
  }));

  const clicked = await page.evaluate(() => {
    const controls = [...document.querySelectorAll('button, input[type="button"], input[type="submit"]')];
    const visible = el => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const score = el => {
      const text = `${el.id || ''} ${el.name || ''} ${el.textContent || ''} ${el.value || ''}`;
      if (/חשב|calculate/i.test(text)) return 3;
      if (/חישוב|run/i.test(text)) return 2;
      return 0;
    };
    const control = controls.filter(visible).sort((a, b) => score(b) - score(a)).find(el => score(el) > 0);
    if (!control) return false;
    control.click();
    return true;
  });
  if (!clicked) throw new Error('Could not find calculation control');
  await page.waitForTimeout(8000);

  const runtime = await page.evaluate(() => {
    let result = null;
    try {
      if (typeof threeStarResultData !== 'undefined' && threeStarResultData) {
        result = {
          found: threeStarResultData.found ?? null,
          reason: threeStarResultData.reason ?? null,
          eventTime: threeStarResultData.eventTime ?? null,
          candidateCount: threeStarResultData.candidateCount ?? null,
          eligibleCandidateCount: threeStarResultData.eligibleCandidateCount ?? null,
          pointwiseCandidateCount: threeStarResultData.pointwiseCandidateCount ?? null,
          visibilityIntervalCandidateCount: threeStarResultData.visibilityIntervalCandidateCount ?? null,
          stars: Array.isArray(threeStarResultData.stars) ? threeStarResultData.stars.map(star => ({
            name: star.name ?? null,
            catalogId: star.catalogId ?? null,
            apparentAltitude: star.apparentAltitude ?? null,
          })) : [],
        };
      }
    } catch (error) {
      result = { readError: String(error?.message || error) };
    }
    return {
      probe: globalThis.__LEVEL_B_THREE_STAR_MIN_ALTITUDE_RUNTIME__ ?? null,
      result,
      inputsAfter: {
        feature: document.querySelector('#calculatorFeature')?.value ?? null,
        minAlt: document.querySelector('#minAlt')?.value ?? null,
        engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
      },
    };
  });

  const diagnostic = { url: page.url(), inputsBefore, ...runtime };
  console.log(JSON.stringify(diagnostic, null, 2));
  if (!runtime.probe) throw new Error('Minimum-altitude runtime probe did not execute');
  if (Number(runtime.probe.minimumStarAltitudeDeg) !== 89) {
    throw new Error(`Runtime read minimum altitude ${runtime.probe.minimumStarAltitudeDeg}, expected 89`);
  }
  if (runtime.probe.engineMode !== 'level-b-v3-crumey-blackwell-equilibrium') {
    throw new Error(`Runtime probe used unexpected engine ${runtime.probe.engineMode}`);
  }
} finally {
  await context.close();
  await browser.close();
}

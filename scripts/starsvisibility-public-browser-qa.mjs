import { chromium } from 'playwright';
import fs from 'node:fs';

const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) {
  throw new Error(`TARGET_URL must be a public https URL; got ${targetUrl || '<empty>'}`);
}

const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile-390', width: 390, height: 844 },
];

const diagnostics = [];
let failed = false;
const browser = await chromium.launch({ headless: true });

async function setStableInputs(page) {
  await page.evaluate(() => {
    const setValue = (el, value) => {
      const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype
        : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype
        : HTMLElement.prototype;
      const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
      if (descriptor?.set) descriptor.set.call(el, String(value));
      else el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };

    const findInput = hints => [...document.querySelectorAll('input')].find(el => {
      const hay = `${el.id} ${el.name} ${el.getAttribute('aria-label') || ''} ${el.closest('label')?.textContent || ''}`.toLowerCase();
      return hints.some(h => hay.includes(h));
    });

    const lat = findInput(['latitude', 'lat', 'רוחב']);
    const lon = findInput(['longitude', 'lon', 'lng', 'אורך']);
    if (lat) setValue(lat, 31.778);
    if (lon) setValue(lon, 35.235);

    const date = document.querySelector('input[type="date"]');
    if (date) setValue(date, '2026-08-17');
  });
}

async function chooseLevelBEngine(page) {
  return page.evaluate(() => {
    const levelBPattern = /level\s*-?\s*b|level_b|sitewide|stellar\s+transport/i;
    for (const select of document.querySelectorAll('select')) {
      const options = [...select.options];
      const option = options.find(o => levelBPattern.test(`${o.value} ${o.textContent || ''}`));
      if (!option) continue;
      select.value = option.value;
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return {
        found: true,
        id: select.id || null,
        name: select.name || null,
        value: option.value,
        text: (option.textContent || '').trim(),
      };
    }
    return {
      found: false,
      selects: [...document.querySelectorAll('select')].map(select => ({
        id: select.id || null,
        name: select.name || null,
        value: select.value,
        options: [...select.options].map(o => ({ value: o.value, text: (o.textContent || '').trim() })),
      })),
    };
  });
}

async function triggerCalculation(page) {
  const clicked = await page.evaluate(() => {
    const controls = [...document.querySelectorAll('button, input[type="button"], input[type="submit"]')];
    const visible = el => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const score = el => {
      const hay = `${el.id || ''} ${el.name || ''} ${el.textContent || ''} ${el.value || ''} ${el.getAttribute('aria-label') || ''}`;
      if (/חשב|calculate/i.test(hay)) return 3;
      if (/חישוב|run/i.test(hay)) return 2;
      return 0;
    };
    const control = controls.filter(visible).sort((a, b) => score(b) - score(a)).find(el => score(el) > 0);
    if (!control) return false;
    control.click();
    return true;
  });
  if (clicked) return 'visible-control';

  const called = await page.evaluate(async () => {
    if (typeof globalThis.calculate !== 'function') return false;
    await globalThis.calculate();
    return true;
  });
  if (called) return 'globalThis.calculate';
  throw new Error('Could not find a visible calculation control or global calculate() function');
}

for (const viewport of viewports) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    locale: 'he-IL',
  });
  const page = await context.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  const failedRequests = [];
  page.on('pageerror', err => pageErrors.push(String(err?.stack || err)));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('requestfailed', req => {
    failedRequests.push({ url: req.url(), error: req.failure()?.errorText || 'unknown' });
  });

  const diag = {
    viewport,
    url: targetUrl,
    httpStatus: null,
    feature: null,
    magnitudeBasis: null,
    magnitudeThreshold: null,
    engineSelection: null,
    trigger: null,
    candidateCountFromText: null,
    resultSnippet: null,
    horizontalOverflowPx: null,
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

    await page.locator('#calculatorFeature').waitFor({ state: 'attached', timeout: 20000 });
    await page.locator('#threeStarMagnitudeBasis').waitFor({ state: 'attached', timeout: 10000 });
    await page.locator('#threeStarMagnitudeThreshold').waitFor({ state: 'attached', timeout: 10000 });

    await page.selectOption('#calculatorFeature', 'three-star');
    await page.selectOption('#threeStarMagnitudeBasis', 'effective');
    await page.locator('#threeStarMagnitudeThreshold').fill('1.7');
    await page.locator('#threeStarMagnitudeThreshold').dispatchEvent('change');
    await setStableInputs(page);
    diag.engineSelection = await chooseLevelBEngine(page);

    diag.feature = await page.locator('#calculatorFeature').inputValue();
    diag.magnitudeBasis = await page.locator('#threeStarMagnitudeBasis').inputValue();
    diag.magnitudeThreshold = await page.locator('#threeStarMagnitudeThreshold').inputValue();
    assert(diag.feature === 'three-star', `Three-Star feature remains selected (got ${diag.feature})`);
    assert(diag.magnitudeBasis === 'effective', `Effective magnitude basis remains selected (got ${diag.magnitudeBasis})`);
    assert(Number(diag.magnitudeThreshold) === 1.7, `Magnitude threshold is 1.7 (got ${diag.magnitudeThreshold})`);

    const before = await page.locator('body').innerText();
    diag.trigger = await triggerCalculation(page);
    await page.waitForTimeout(5000);
    const after = await page.locator('body').innerText();
    assert(after !== before, 'Calculation updates visible page content');

    const candidateMatch = after.match(/(\d+)\s+מועמדים(?:\s+שעברו\s+את\s+תנאי\s+הבחירה)?\s+נסרקו/);
    if (candidateMatch) diag.candidateCountFromText = Number(candidateMatch[1]);
    const resultLine = after.split(/\n+/).find(line => /זמן שלושה כוכבים|שלושה כוכבים|Three.?Star/i.test(line));
    diag.resultSnippet = resultLine?.slice(0, 500) || after.slice(-500);

    const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    diag.horizontalOverflowPx = overflow;
    assert(overflow <= 1, `No page-wide horizontal overflow (got ${overflow}px)`);
    assert(pageErrors.length === 0, `No uncaught page errors (got ${pageErrors.length})`);

    if (candidateMatch) {
      assert(diag.candidateCountFromText > 0, `Three-Star diagnostics do not report zero scanned candidates (got ${diag.candidateCountFromText})`);
    }

    await page.screenshot({ path: `qa-artifacts/${viewport.name}.png`, fullPage: true });
  } catch (error) {
    failed = true;
    diag.fatalError = String(error?.stack || error);
    try {
      await page.screenshot({ path: `qa-artifacts/${viewport.name}-failure.png`, fullPage: true });
    } catch {}
  } finally {
    diagnostics.push(diag);
    await context.close();
  }
}

await browser.close();
fs.writeFileSync('qa-artifacts/diagnostics.json', JSON.stringify(diagnostics, null, 2));
console.log(JSON.stringify(diagnostics, null, 2));
if (failed) process.exitCode = 1;

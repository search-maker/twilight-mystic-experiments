import { chromium } from 'playwright';
import fs from 'node:fs';

const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const viewports = [
  { name: 'no-event-desktop', width: 1440, height: 1000 },
  { name: 'no-event-mobile-390', width: 390, height: 844 },
];

const diagnostics = [];
let failed = false;
const browser = await chromium.launch({ headless: true });

async function setValue(page, selector, value) {
  const locator = page.locator(selector);
  const tag = await locator.evaluate(el => el.tagName);
  if (tag === 'SELECT') {
    await locator.selectOption(String(value));
    return;
  }
  await locator.evaluate((el, nextValue) => {
    const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(el, String(nextValue));
    else el.value = String(nextValue);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

async function selectLevelBEquilibrium(page) {
  return page.evaluate(() => {
    const select = document.querySelector('#visibilityEngineMode');
    if (!(select instanceof HTMLSelectElement)) return false;
    const option = [...select.options].find(o => o.value === 'level-b-v3-crumey-blackwell-equilibrium');
    if (!option) return false;
    select.value = option.value;
    select.dispatchEvent(new Event('input', { bubbles: true }));
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  });
}

async function setThreeStarCount(page) {
  return page.evaluate(() => {
    const select = document.querySelector('#threeStarCount');
    if (!(select instanceof HTMLSelectElement)) return { found: false };
    const option = [...select.options].find(o => o.value === '3');
    if (!option) return { found: false, options: [...select.options].map(o => o.value) };
    select.value = option.value;
    select.dispatchEvent(new Event('input', { bubbles: true }));
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return { found: true, value: select.value, options: [...select.options].map(o => o.value) };
  });
}

async function setHighMinimumStarAltitude(page) {
  return page.evaluate(() => {
    const inputs = [...document.querySelectorAll('input')]
      .filter(input => input.type !== 'hidden' && input.type !== 'date');

    const describe = input => {
      const id = input.id || '';
      const name = input.name || '';
      const aria = input.getAttribute('aria-label') || '';
      const labelledBy = input.getAttribute('aria-labelledby') || '';
      const labelledText = labelledBy
        ? labelledBy.split(/\s+/).map(idref => document.getElementById(idref)?.textContent || '').join(' ')
        : '';
      const label = input.labels ? [...input.labels].map(el => el.textContent || '').join(' ') : '';
      const parent = input.parentElement?.textContent || '';
      const grandparent = input.parentElement?.parentElement?.textContent || '';
      const context = `${id} ${name} ${aria} ${labelledText} ${label} ${parent} ${grandparent}`.replace(/\s+/g, ' ').trim();
      return { input, id, name, context };
    };

    const described = inputs.map(describe);
    const score = ({ id, name, context, input }) => {
      const key = `${id} ${name}`.toLowerCase();
      const text = context.toLowerCase();
      if (/latitude|longitude|\blat\b|\blon\b|\blng\b/.test(key)) return -100;
      if (/magnitude|mag/.test(key) || /magnitude/.test(text)) return -50;
      let points = 0;
      if (/altitude|elevation|alt|minalt|min_alt/.test(key)) points += 25;
      if (/minimum star altitude|minimum altitude|star altitude|altitude.*star/.test(text)) points += 40;
      if (/גובה/.test(context) && /כוכב/.test(context)) points += 40;
      if (/minimum|min/.test(text)) points += 5;
      if (String(input.value) === '3') points += 3;
      return points;
    };

    const ranked = described
      .map(item => ({ ...item, score: score(item) }))
      .sort((a, b) => b.score - a.score);
    const selected = ranked[0];
    if (!selected || selected.score <= 0) {
      return {
        found: false,
        candidates: ranked.slice(0, 12).map(item => ({
          id: item.id,
          name: item.name,
          value: item.input.value,
          type: item.input.type,
          score: item.score,
          context: item.context.slice(0, 240),
        })),
      };
    }

    const input = selected.input;
    const before = input.value;
    const min = input.getAttribute('min');
    const max = input.getAttribute('max');
    const step = input.getAttribute('step');
    const maxNumber = Number(max);
    const target = Number.isFinite(maxNumber) && max !== '' ? Math.min(89, maxNumber) : 89;
    const proto = HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(input, String(target));
    else input.value = String(target);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));

    return {
      found: true,
      id: selected.id,
      name: selected.name,
      score: selected.score,
      before,
      value: input.value,
      target,
      min,
      max,
      step,
      valid: typeof input.checkValidity === 'function' ? input.checkValidity() : null,
      validationMessage: input.validationMessage || '',
      context: selected.context.slice(0, 300),
    };
  });
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
        globalThis.__noEventQaFeatureHistory.push(String(nextValue));
        descriptor.set.call(this, String(nextValue));
      },
    });
  });
}

async function clickCalculate(page) {
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
  if (!clicked) throw new Error('Could not find a visible calculation control');
}

for (const viewport of viewports) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, locale: 'he-IL' });
  const page = await context.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  const failedRequests = [];
  page.on('pageerror', err => pageErrors.push(String(err?.stack || err)));
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('requestfailed', req => failedRequests.push({ url: req.url(), error: req.failure()?.errorText || 'unknown' }));

  const diag = {
    viewport,
    httpStatus: null,
    countControl: null,
    altitudeControl: null,
    featureHistory: [],
    candidateDiagnosticLine: null,
    candidateCount: null,
    resultExcerpt: null,
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

    await setValue(page, '#calculatorFeature', 'three-star');
    await setValue(page, '#threeStarMagnitudeBasis', 'effective');
    await setValue(page, '#threeStarMagnitudeThreshold', '1.7');
    diag.countControl = await setThreeStarCount(page);
    diag.altitudeControl = await setHighMinimumStarAltitude(page);

    assert(await selectLevelBEquilibrium(page), 'Level-B equilibrium calculation engine is available and selected');
    assert(await page.locator('#calculatorFeature').inputValue() === 'three-star', 'Three-Star is selected before high-altitude no-event calculation');
    assert(await page.locator('#threeStarMagnitudeBasis').inputValue() === 'effective', 'Effective magnitude basis is selected');
    assert(Number(await page.locator('#threeStarMagnitudeThreshold').inputValue()) === 1.7, 'Effective threshold remains 1.7');
    assert(diag.countControl.found && diag.countControl.value === '3', 'Three-Star required count is 3');
    assert(diag.altitudeControl.found, 'Minimum star altitude control was found');
    if (diag.altitudeControl.found) {
      assert(Number(diag.altitudeControl.value) >= 80, `Minimum star altitude was raised to a legal high value (got ${diag.altitudeControl.value}°)`);
      assert(diag.altitudeControl.valid !== false, `High altitude input passes browser validity (${diag.altitudeControl.validationMessage || 'valid'})`);
    }

    await installFeatureAudit(page);
    await clickCalculate(page);
    await page.waitForTimeout(8000);

    diag.featureHistory = await page.evaluate(() => [...(globalThis.__noEventQaFeatureHistory || [])]);
    assert(diag.featureHistory.every(value => value === 'three-star'),
      `Three-Star never routes through Standard in no-event calculation (history: ${JSON.stringify(diag.featureHistory)})`);

    const body = await page.locator('body').innerText();
    const lines = body.split(/\n+/).map(line => line.trim()).filter(Boolean);
    const candidateLine = lines.find(line => /(?:candidate|מועמד)/i.test(line) && /(?:scan|נסרק)/i.test(line))
      || lines.find(line => /(?:candidate|מועמד)/i.test(line) && /\d+/.test(line));
    diag.candidateDiagnosticLine = candidateLine || null;
    const candidateMatch = candidateLine?.match(/(\d+)/);
    diag.candidateCount = candidateMatch ? Number(candidateMatch[1]) : null;
    diag.resultExcerpt = lines.filter(line => /Three.?Star|שלושה כוכבים|candidate|מועמד|not found|לא נמצא|altitude|גובה/i.test(line)).slice(-12).join(' | ');

    const verifiedEvent = /Three-star time:\s*\d{1,2}:\d{2}\s*[·-]\s*Verified/i.test(body);
    assert(!verifiedEvent, `High-altitude fixture produces a no-event result (altitude=${diag.altitudeControl?.value || 'unknown'}°)`);
    assert(Boolean(candidateLine), 'No-event result renders candidate diagnostics');
    assert(Number.isFinite(diag.candidateCount) && diag.candidateCount > 0,
      `No-event diagnostics report a nonzero scanned-candidate count (got ${diag.candidateCount})`);

    const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    diag.horizontalOverflowPx = overflow;
    assert(overflow <= 1, `No page-wide horizontal overflow in no-event result (got ${overflow}px)`);
    assert(pageErrors.length === 0, `No uncaught page errors (got ${pageErrors.length})`);
    assert(consoleErrors.length === 0, `No console errors (got ${consoleErrors.length})`);
    assert(failedRequests.length === 0, `No failed network requests (got ${failedRequests.length})`);

    await page.screenshot({ path: `qa-artifacts/${viewport.name}.png`, fullPage: true });
  } catch (error) {
    failed = true;
    diag.fatalError = String(error?.stack || error);
    try { await page.screenshot({ path: `qa-artifacts/${viewport.name}-failure.png`, fullPage: true }); } catch {}
  } finally {
    diagnostics.push(diag);
    await context.close();
  }
}

await browser.close();
fs.writeFileSync('qa-artifacts/no-event-diagnostics.json', JSON.stringify(diagnostics, null, 2));
console.log(JSON.stringify(diagnostics, null, 2));
if (failed) process.exitCode = 1;

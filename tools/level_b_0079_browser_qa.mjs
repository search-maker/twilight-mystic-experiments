import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';

const baseUrl = new URL('./level_b_0079_browser_qa_base.mjs', import.meta.url);
const runtimeUrl = new URL('./.level_b_0079_browser_qa_runtime.mjs', import.meta.url);
const source = readFileSync(baseUrl, 'utf8');

function replaceExactly(text, oldText, newText, name) {
  const count = text.split(oldText).length - 1;
  if (count !== 1) throw new Error(`Expected exactly one ${name} anchor, found ${count}`);
  if (text.includes(newText)) throw new Error(`Base QA unexpectedly already contains ${name} fix`);
  return text.replace(oldText, newText);
}

let patched = source;
patched = replaceExactly(
  patched,
  "document.querySelector('#comparisonView')",
  "document.querySelector('#threeStarComparisonView')",
  'comparison-view-selector',
);

patched = replaceExactly(
  patched,
  "  await waitGlobal(page, 'comparisonResultsFinal === true && Array.isArray(comparisonResultsA) && comparisonResultsA.length === 1 && Array.isArray(comparisonResultsB) && comparisonResultsB.length === 1', 360000);\n  const a = jsonClone(await globalEval(page, 'comparisonResultsA'));",
  `  await waitGlobal(page, 'comparisonResultsFinal === true && Array.isArray(comparisonResultsA) && comparisonResultsA.length === 1 && Array.isArray(comparisonResultsB) && comparisonResultsB.length === 1', 360000);
  await page.waitForFunction(() => {
    const button = document.querySelector('#calculateComparison');
    const cancel = document.querySelector('#cancelComparison');
    const cancelActive = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && !cancel.disabled);
    return Boolean(button && !button.disabled && button.getAttribute('aria-busy') !== 'true' && !cancelActive);
  }, undefined, { timeout: 60000 });
  const a = jsonClone(await globalEval(page, 'comparisonResultsA'));`,
  'comparison-terminal-idle-before-next-route',
);

patched = replaceExactly(
  patched,
  "  await page.evaluate(() => { const el = document.querySelector('#weeklyView'); if (el && !el.open) el.querySelector('summary')?.click(); });\n  await waitGlobal(page, 'weeklyResultsFinal === true && Array.isArray(weeklyResults) && weeklyResults.length === 7');",
  `  await page.click('#calculate');
  await waitDailyDone(page);
  const weeklyBaseline = jsonClone(await globalEval(page, 'threeStarResultData'));
  assert(weeklyBaseline && weeklyBaseline.calculationEngine === engine, engine + '/weekly prerequisite Three-Star baseline did not bind current engine');

  const readWeeklyState = () => page.evaluate(() => {
    const lexical = expression => {
      try { return window.eval(expression); } catch (_) { return null; }
    };
    const rows = typeof weeklyResults !== 'undefined' && Array.isArray(weeklyResults) ? weeklyResults : [];
    const final = typeof weeklyResultsFinal !== 'undefined' ? weeklyResultsFinal : null;
    const cancel = document.querySelector('#cancelWeekly');
    const calculate = document.querySelector('#calculateWeekly');
    const cancelVisible = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && getComputedStyle(cancel).visibility !== 'hidden' && !cancel.disabled);
    const activeWorkerValue = lexical("typeof activeWeeklyWorker !== 'undefined' ? activeWeeklyWorker : null");
    const versionValue = lexical("typeof weeklyCalculationVersion !== 'undefined' ? weeklyCalculationVersion : null");
    const engineOf = row => row?.calculationEngine ?? row?.levelBRunProvenance?.calculationEngine ?? null;
    return {
      weeklyResultsFinal: final,
      weeklyResultsLength: rows.length,
      pendingCount: rows.filter(row => Boolean(row?.pending)).length,
      provisionalCount: rows.filter(row => Boolean(row?.provisional)).length,
      verifiedCount: rows.filter(row => row && !row.pending && row.provisional === false).length,
      engines: [...new Set(rows.map(engineOf).filter(Boolean))],
      weeklyGridChildCount: document.querySelector('#weeklyResultsGrid')?.children?.length ?? null,
      weeklyProgressValue: Number(document.querySelector('#weeklyProgressBar')?.value ?? 0),
      weeklyProgressText: String(document.querySelector('#weeklyProgressText')?.textContent || '').trim().slice(0, 500),
      calculateWeeklyDisabled: calculate?.disabled ?? null,
      cancelWeeklyVisible: cancelVisible,
      activeWeeklyWorker: activeWorkerValue == null ? null : Boolean(activeWorkerValue),
      weeklyCalculationVersion: Number.isFinite(Number(versionValue)) ? Number(versionValue) : null,
      errorText: String(document.querySelector('#error')?.textContent || '').trim().slice(0, 500),
      weeklyOpen: document.querySelector('#weeklyView')?.open ?? null,
      engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
    };
  });
  const isWeeklyTerminal = state => state.weeklyResultsFinal === true && state.weeklyResultsLength === 7 && state.pendingCount === 0 && state.calculateWeeklyDisabled === false && state.cancelWeeklyVisible === false;
  const isWeeklyActive = (state, minVersion) => state.weeklyResultsFinal === false && state.weeklyResultsLength === 7 && state.pendingCount > 0 && state.calculateWeeklyDisabled === true && state.cancelWeeklyVisible === true && state.activeWeeklyWorker === true && Number.isFinite(state.weeklyCalculationVersion) && state.weeklyCalculationVersion > minVersion;

  const beforeOpen = await readWeeklyState();
  const baselineVersion = Number.isFinite(beforeOpen.weeklyCalculationVersion) ? beforeOpen.weeklyCalculationVersion : -1;
  const weeklyDetails = page.locator('#weeklyView');
  await weeklyDetails.waitFor({ state: 'visible', timeout: 60000 });
  if (await weeklyDetails.evaluate(el => el.open)) {
    await weeklyDetails.locator('summary').click();
    await page.waitForFunction(() => document.querySelector('#weeklyView')?.open === false, undefined, { timeout: 10000 });
  }
  await weeklyDetails.locator('summary').click();
  await page.waitForFunction(() => document.querySelector('#weeklyView')?.open === true, undefined, { timeout: 10000 });

  const proveStableStartOrTerminal = async minVersion => {
    let first;
    try {
      await page.waitForFunction(({ minVersion }) => {
        const lexical = expression => {
          try { return window.eval(expression); } catch (_) { return null; }
        };
        const rows = typeof weeklyResults !== 'undefined' && Array.isArray(weeklyResults) ? weeklyResults : [];
        const final = typeof weeklyResultsFinal !== 'undefined' ? weeklyResultsFinal : null;
        const calculate = document.querySelector('#calculateWeekly');
        const cancel = document.querySelector('#cancelWeekly');
        const cancelVisible = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && getComputedStyle(cancel).visibility !== 'hidden' && !cancel.disabled);
        const activeWorker = lexical("typeof activeWeeklyWorker !== 'undefined' ? activeWeeklyWorker : null");
        const version = Number(lexical("typeof weeklyCalculationVersion !== 'undefined' ? weeklyCalculationVersion : NaN"));
        const terminal = final === true && rows.length === 7 && rows.every(row => !row?.pending) && calculate && !calculate.disabled && !cancelVisible;
        const active = final === false && rows.length === 7 && rows.some(row => Boolean(row?.pending)) && calculate?.disabled === true && cancelVisible && Boolean(activeWorker) && Number.isFinite(version) && version > minVersion;
        return terminal || active;
      }, { minVersion }, { timeout: 15000 });
      first = await readWeeklyState();
    } catch (_) {
      return { proven: false, terminal: false, first: await readWeeklyState(), second: null };
    }
    if (isWeeklyTerminal(first)) return { proven: true, terminal: true, first, second: first };
    await page.waitForTimeout(1200);
    const second = await readWeeklyState();
    if (isWeeklyTerminal(second)) return { proven: true, terminal: true, first, second };
    return { proven: isWeeklyActive(first, minVersion) && isWeeklyActive(second, minVersion), terminal: false, first, second };
  };

  let startMethod = 'auto-toggle';
  let proof = await proveStableStartOrTerminal(baselineVersion);
  if (!proof.proven) {
    const idle = await readWeeklyState();
    const canSingleClick = idle.activeWeeklyWorker !== true && idle.cancelWeeklyVisible === false && idle.calculateWeeklyDisabled === false;
    if (!canSingleClick) {
      report.batch.push({ engine, feature: 'weekly-start-ambiguous-diagnostic', beforeOpen, proof, idle });
      throw new Error(engine + '/weekly did not expose stable auto-start or a safe idle single-click fallback: ' + JSON.stringify({ beforeOpen, proof, idle }));
    }
    startMethod = 'single-click-fallback';
    await page.click('#calculateWeekly');
    proof = await proveStableStartOrTerminal(baselineVersion);
    if (!proof.proven) {
      const failed = await readWeeklyState();
      report.batch.push({ engine, feature: 'weekly-start-failed-diagnostic', beforeOpen, proof, failed });
      throw new Error(engine + '/weekly single-click fallback produced no stable worker-backed Weekly state transition: ' + JSON.stringify({ beforeOpen, proof, failed }));
    }
  }

  if (!proof.terminal) {
    const startedVersion = Math.max(
      baselineVersion + 1,
      Number.isFinite(proof.second?.weeklyCalculationVersion) ? proof.second.weeklyCalculationVersion : baselineVersion + 1,
    );
    try {
      await page.waitForFunction(({ startedVersion }) => {
        const lexical = expression => {
          try { return window.eval(expression); } catch (_) { return null; }
        };
        const rows = typeof weeklyResults !== 'undefined' && Array.isArray(weeklyResults) ? weeklyResults : [];
        const final = typeof weeklyResultsFinal !== 'undefined' ? weeklyResultsFinal : null;
        const calculate = document.querySelector('#calculateWeekly');
        const cancel = document.querySelector('#cancelWeekly');
        const cancelVisible = Boolean(cancel && !cancel.hidden && getComputedStyle(cancel).display !== 'none' && getComputedStyle(cancel).visibility !== 'hidden' && !cancel.disabled);
        const activeWorker = lexical("typeof activeWeeklyWorker !== 'undefined' ? activeWeeklyWorker : null");
        const version = Number(lexical("typeof weeklyCalculationVersion !== 'undefined' ? weeklyCalculationVersion : NaN"));
        const terminal = final === true && rows.length === 7 && rows.every(row => !row?.pending) && calculate && !calculate.disabled && !cancelVisible;
        const silentAbort = Number.isFinite(version) && version >= startedVersion && !Boolean(activeWorker) && final === true && rows.length === 0 && calculate && !calculate.disabled && !cancelVisible;
        return terminal || silentAbort;
      }, { startedVersion }, { timeout: 300000 });
    } catch (error) {
      const diagnostic = await readWeeklyState();
      report.batch.push({ engine, feature: 'weekly-terminal-timeout-diagnostic', timeoutMs: 300000, startMethod, beforeOpen, proof, diagnostic });
      throw new Error(engine + '/weekly worker-backed run did not reach terminal state within 300000ms: ' + JSON.stringify(diagnostic), { cause: error });
    }
    const terminal = await readWeeklyState();
    if (!isWeeklyTerminal(terminal)) {
      report.batch.push({ engine, feature: 'weekly-silent-abort-diagnostic', startMethod, beforeOpen, proof, terminal });
      throw new Error(engine + '/weekly worker-backed run aborted back to idle without seven terminal dates: ' + JSON.stringify(terminal));
    }
  }`,
  'weekly-stable-worker-backed-single-start',
);

patched = replaceExactly(
  patched,
  "async function runAnnualMonthAndExport(page, engine) {\n  await waitCalculateReady(page);\n  await selectEngine(page, engine);\n  await chooseFeature(page, 'three-star');\n  await page.evaluate(() => {",
  `async function runAnnualMonthAndExport(page, engine) {
  await waitCalculateReady(page);
  await selectEngine(page, engine);
  await chooseFeature(page, 'three-star');
  await page.click('#calculate');
  await waitDailyDone(page);
  const annualBaseline = jsonClone(await globalEval(page, 'threeStarResultData'));
  assert(annualBaseline && annualBaseline.calculationEngine === engine, engine + '/annual prerequisite Three-Star baseline did not bind current engine');
  await page.evaluate(() => {`,
  'annual-current-engine-baseline',
);

writeFileSync(runtimeUrl, patched);
try {
  await import(`${runtimeUrl.href}?runner-fix-v8`);
} finally {
  try { unlinkSync(runtimeUrl); } catch (_) {}
}

import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const consoleLines = [];
  page.on('console', m => consoleLines.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => consoleLines.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async () => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', 31.778);
    set('lon', 35.235);
    set('date', '2026-03-19');
    set('timezone', 'Asia/Jerusalem');
    set('observerElevationM', 800);
    set('visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium');
    set('threeStarCount', 3);
    set('threeStarMagnitudeBasis', 'effective');
    set('threeStarMagnitudeThreshold', 1.7);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = 'level-b-v3-crumey-blackwell-equilibrium';
    globalThis.__SKY_MAP_REQUEST__ = false;

    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    const catalogCount = Array.isArray(globalThis.__STARS_BUILT_IN_STARS__) ? globalThis.__STARS_BUILT_IN_STARS__.length : -1;
    const scaffoldSource = String(eval('__levelBSitewideRunUsingLegacyScaffold'));
    const calculateSource = String(eval('calculate'));

    let error = null;
    try {
      await eval('__levelBSitewideRunUsingLegacyScaffold("level-b-v3-crumey-blackwell-equilibrium")');
    } catch (e) {
      error = String(e?.stack || e);
    }
    const result = JSON.parse(JSON.stringify(eval('threeStarResultData')));
    return {
      catalogCount,
      error,
      result,
      directCatalogGlobalAfterFinally: globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__ === undefined ? 'deleted' : 'present',
      catalogOnlyFlagAfterFinally: globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__ === undefined ? 'deleted' : String(globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__),
      scaffoldHasHandoff: scaffoldSource.includes('LEVEL-B-THREE-STAR-DIRECT-CATALOG-HANDOFF-V3') || calculateSource.includes('LEVEL-B-THREE-STAR-DIRECT-CATALOG-HANDOFF-V3'),
      calculateHasWorkerBypass: calculateSource.includes('LEVEL-B-THREE-STAR-CATALOG-ONLY-WORKER-BYPASS-V1'),
    };
  });

  const evaluated = Number(audit?.result?.evaluatedTargetCount);
  if (audit.catalogCount !== 9090) throw new Error(`Expected catalogCount=9090, got ${audit.catalogCount}`);
  if (audit.error) throw new Error(`Scaffold runtime error: ${audit.error}`);
  if (!audit.calculateHasWorkerBypass) throw new Error('Worker bypass marker missing at runtime');
  if (!audit.scaffoldHasHandoff) throw new Error('Direct catalog handoff marker missing at runtime');
  if (!Number.isFinite(evaluated) || evaluated < 1000) throw new Error(`Expected >1000 evaluated targets, got ${audit?.result?.evaluatedTargetCount}`);
  if (audit.directCatalogGlobalAfterFinally !== 'deleted') throw new Error('Direct catalog global was not cleaned up');
  if (audit.catalogOnlyFlagAfterFinally !== 'deleted') throw new Error('Catalog-only flag was not cleaned up');

  const output = {
    schemaVersion: 1,
    status: 'PR109_CURRENT_HEAD_RUNTIME_PASS',
    applicationSha: process.env.APPLICATION_SHA,
    audit,
    browserConsole: consoleLines,
    claimBoundary: { noScienceParameterChange: true, noMYSTIC: true, noPandora: true },
  };
  const outDir = path.join(process.env.RUNNER_TEMP, 'pr109-runtime-audit');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(output, null, 2) + '\n');
  console.log('PR109_RUNTIME_AUDIT=' + JSON.stringify(audit));
} finally {
  await browser.close();
}

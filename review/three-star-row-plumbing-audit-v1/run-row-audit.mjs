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
    const safely = (fn) => { try { return fn(); } catch (error) { return { error: String(error?.message || error) }; } };
    const summarizeRows = (value) => ({
      isArray: Array.isArray(value),
      length: Array.isArray(value) ? value.length : null,
      first5: Array.isArray(value) ? value.slice(0, 5).map(r => ({ name:r?.name ?? null, hip:r?.hip ?? null, mag:r?.mag ?? null, ra:r?.raHours ?? r?.ra ?? null, dec:r?.decDeg ?? r?.dec ?? null })) : null,
    });
    const source = (name) => safely(() => String(eval(name)));
    const sourceSummary = (name) => {
      const text = source(name);
      if (typeof text !== 'string') return text;
      return {
        length: text.length,
        hasDirectRuntimeMarker: text.includes('LEVEL-B-THREE-STAR-DIRECT-CATALOG-RUNTIME-V2'),
        hasDirectHookMarker: text.includes('LEVEL-B-THREE-STAR-DIRECT-CATALOG-HOOK-V2'),
        hasCatalogOnlyFlag: text.includes('__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__'),
        hasRowsCatalogAssignment: text.includes('rows = catalog.map'),
        hasPostprocessCall: text.includes('__levelBSitewidePostprocess'),
        prefix: text.slice(0, 1200),
      };
    };
    const snap = (label) => {
      const builtIn = safely(() => eval('builtInStars'));
      const rows = safely(() => eval('rows'));
      const globalCatalog = globalThis.__STARS_BUILT_IN_STARS__;
      return {
        label,
        builtInStars: summarizeRows(builtIn),
        rows: summarizeRows(rows),
        globalCatalog: summarizeRows(globalCatalog),
        builtInSameAsGlobal: safely(() => builtIn === globalCatalog),
        rowsSameAsBuiltIn: safely(() => rows === builtIn),
        rowsSameAsGlobal: safely(() => rows === globalCatalog),
        calculatorFeature: document.getElementById('calculatorFeature')?.value ?? null,
        engineMode: document.getElementById('visibilityEngineMode')?.value ?? globalThis.__STAR_VISIBILITY_ENGINE_MODE__ ?? null,
      };
    };

    try { localStorage.clear(); } catch (_) {}
    const set = (id, value) => { const el=document.getElementById(id); if(!el) throw new Error(`missing #${id}`); el.value=String(value); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); };
    if (document.getElementById('calculatorFeature')) set('calculatorFeature','three-star');
    set('lat',31.778); set('lon',35.235); set('date','2026-03-19');
    if(document.getElementById('timezone')) set('timezone','Asia/Jerusalem');
    set('observerElevationM',800);
    set('visibilityEngineMode','level-b-v3-crumey-blackwell-equilibrium');
    set('threeStarCount',3); set('threeStarMagnitudeBasis','effective'); set('threeStarMagnitudeThreshold',1.7);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__='level-b-v3-crumey-blackwell-equilibrium';
    globalThis.__SKY_MAP_REQUEST__=true;

    const sourceBefore = {
      calculate: sourceSummary('calculate'),
      scaffold: sourceSummary('__levelBSitewideRunUsingLegacyScaffold'),
      postprocess: sourceSummary('__levelBSitewidePostprocess'),
    };
    const snapshots = [snap('before-catalog-ready')];
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    snapshots.push(snap('after-catalog-ready'));

    let rawCalculateError = null;
    try { await eval('calculate()'); } catch (error) { rawCalculateError = String(error?.stack || error); }
    snapshots.push(snap('after-raw-calculate'));

    let scaffoldError = null;
    try { await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)'); }
    catch (error) { scaffoldError = String(error?.stack || error); }
    snapshots.push(snap('after-level-b-scaffold'));

    const result = safely(() => eval('threeStarResultData'));
    return {
      sourceBefore,
      snapshots,
      rawCalculateError,
      scaffoldError,
      threeStarResult: result,
      sourceMarkers: {
        hasCatalogReady: safely(() => typeof eval('ensureBuiltInCatalogReady')),
        hasScaffold: safely(() => typeof eval('__levelBSitewideRunUsingLegacyScaffold')),
        builtCatalogGlobalLength: globalThis.__STARS_BUILT_IN_STARS__?.length ?? null,
      },
    };
  });

  const output = {
    schemaVersion: 2,
    status: 'THREE_STAR_ROW_PLUMBING_RUNTIME_AUDIT',
    applicationSha: process.env.APPLICATION_SHA,
    audit,
    browserConsole: consoleLines,
    claimBoundary: { readOnlyAudit:true, noScienceParameterChange:true, noMYSTIC:true, noPandora:true },
  };
  const outDir = path.join(process.env.RUNNER_TEMP,'three-star-row-plumbing-audit');
  fs.mkdirSync(outDir,{recursive:true});
  fs.writeFileSync(path.join(outDir,'summary.json'),JSON.stringify(output,null,2)+'\n');
  console.log('ROW_PLUMBING_AUDIT='+JSON.stringify(audit));
} finally {
  await browser.close();
}

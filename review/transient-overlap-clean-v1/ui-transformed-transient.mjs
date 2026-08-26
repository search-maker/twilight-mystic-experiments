import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  'tishrei-transient-overlap': '2025-09-23',
  'tammuz-transient-overlap': '2026-06-16',
};
const label = process.env.CASE_LABEL;
const civilDate = CASES[label];
if (!civilDate) throw new Error(`unknown CASE_LABEL ${label}`);
const spec = Object.freeze({
  label,
  civilDate,
  latitudeDeg: 31.778,
  longitudeDeg: 35.235,
  observerElevationM: 800,
  timeZone: 'Asia/Jerusalem',
  engineMode: 'level-b-v3-crumey-blackwell-transient-experimental',
  magnitudeBasis: 'effective',
  magnitudeThreshold: 1.7,
  requiredCount: 3,
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const payload = await page.evaluate(async spec => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg);
    set('lon', spec.longitudeDeg);
    set('date', spec.civilDate);
    set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode);
    set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', spec.magnitudeBasis);
    set('threeStarMagnitudeThreshold', spec.magnitudeThreshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');

    const sunsetMs = Number(eval('sunsetAtSeaLevel')(spec.civilDate, spec.timeZone, spec.latitudeDeg, spec.longitudeDeg));
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, sunsetMs);
    const directSunAltitude = Number(eval('sunAltitude')(sunsetMs, spec.latitudeDeg, spec.longitudeDeg));

    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const result = JSON.parse(JSON.stringify(eval('threeStarResultData')));
    const metadata = JSON.parse(JSON.stringify(eval('lastRunMetadata')));
    const localRows = eval('rows');
    if (!Array.isArray(localRows)) throw new Error('date-transformed local rows unavailable');

    const statusCounts = {};
    const reasonCounts = {};
    let oldPrehistoryErrorCount = 0;
    let missingSunsetDepthCount = 0;
    let transientResultCount = 0;
    let intervalRowCount = 0;
    const supportedFirstVisible = [];
    for (const row of localRows) {
      if (!row || typeof row !== 'object') continue;
      const status = row.levelBStatus ?? null;
      const reason = row.levelBReason ?? null;
      if (status != null) {
        transientResultCount += 1;
        statusCounts[status] = (statusCounts[status] || 0) + 1;
      }
      if (reason != null) reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
      if (reason === 'TRANSIENT_SUNSET_PREHISTORY_REJECTED' || String(reason).includes('SUNSET_PREHISTORY')) oldPrehistoryErrorCount += 1;
      if (reason === 'APPLICATION_SUNSET_SOLAR_DEPRESSION_REQUIRED_FOR_CONTINUOUS_ADAPTATION') missingSunsetDepthCount += 1;
      if (Array.isArray(row.levelBVisibilityIntervalsMs) && row.levelBVisibilityIntervalsMs.length) intervalRowCount += 1;
      if (status === 'SUPPORTED' && Number.isFinite(row.physicalFirstVisibleTime)) {
        supportedFirstVisible.push({
          name: row.name ?? null,
          hr: row.hr ?? null,
          hip: row.hip ?? null,
          catalogMagnitude: row.magOriginal ?? row.mag ?? null,
          effectiveMagnitude: row.physicalEffectiveMag ?? null,
          firstVisibleTimeMs: row.physicalFirstVisibleTime,
          minutesAfterSunset: (row.physicalFirstVisibleTime - sunsetMs) / 60000,
          limitingVMagnitude: row.localLimitingMag ?? null,
          visibilityMarginMag: row.firstVisibleMarginMag ?? null,
          reason,
        });
      }
    }
    supportedFirstVisible.sort((a,b) => a.firstVisibleTimeMs - b.firstVisibleTimeMs);

    return {
      localRowCount: localRows.length,
      transientResultCount,
      intervalRowCount,
      statusCounts,
      reasonCounts,
      oldPrehistoryErrorCount,
      missingSunsetDepthCount,
      sunsetMs,
      directSunAltitudeAtSunsetDeg: directSunAltitude,
      hooksSunDepressionAtSunsetDeg: hooks.sunDepressionAtSunsetDeg,
      metadataSunDepressionAtSunsetDeg: metadata.levelBTransientApplicationSunsetSunDepressionDeg ?? null,
      result,
      earliestSupportedRows: supportedFirstVisible.slice(0, 20),
      directCatalogGlobalAfterFinally: globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__ === undefined ? 'deleted' : 'present',
      catalogOnlyFlagAfterFinally: globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__ === undefined ? 'deleted' : 'present',
    };
  }, spec);

  if (payload.localRowCount < 1000 || payload.transientResultCount < 1000) {
    throw new Error(`insufficient transformed transient rows: ${payload.localRowCount}/${payload.transientResultCount}`);
  }
  if (payload.oldPrehistoryErrorCount !== 0) throw new Error(`old sunset-prehistory rejection remains on ${payload.oldPrehistoryErrorCount} rows`);
  if (payload.missingSunsetDepthCount !== 0) throw new Error(`sunset-depth plumbing missing on ${payload.missingSunsetDepthCount} rows`);
  const expectedDep = -payload.directSunAltitudeAtSunsetDeg;
  if (!(expectedDep > 0.82 && expectedDep < 0.85)) throw new Error(`unexpected application sunset depression ${expectedDep}`);
  if (Math.abs(payload.hooksSunDepressionAtSunsetDeg - expectedDep) > 1e-9) throw new Error('geometry hook sunset depth does not match direct sunAltitude');
  if (Math.abs(payload.metadataSunDepressionAtSunsetDeg - expectedDep) > 1e-9) throw new Error('run metadata lost application sunset depth');
  if (payload.directCatalogGlobalAfterFinally !== 'deleted' || payload.catalogOnlyFlagAfterFinally !== 'deleted') throw new Error('temporary catalog handoff state leaked');

  const outDir = path.join(process.env.RUNNER_TEMP, 'transient-ui-transformed');
  fs.mkdirSync(outDir, { recursive: true });
  const output = {
    schemaVersion: 1,
    status: 'PR111_TRANSFORMED_UI_TRANSIENT_DIAGNOSTIC_PASS',
    applicationSha: process.env.APPLICATION_SHA,
    spec,
    payload,
    claimBoundary: {
      softwareRegressionOnly: true,
      transformedApplicationRows: true,
      fieldFactor314Unchanged: true,
      tauUnchanged: true,
      equilibriumPathUnchanged: true,
      noTuning: true,
      productionAuthorized: false,
      measuredRealSkyValidated: false,
      humanFirstSeeingValidated: false,
      noMYSTIC: true,
    },
    browserConsole,
  };
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(output, null, 2) + '\n');
  console.log('TRANSFORMED_UI_TRANSIENT=' + JSON.stringify({
    label,
    localRowCount: payload.localRowCount,
    transientResultCount: payload.transientResultCount,
    intervalRowCount: payload.intervalRowCount,
    oldPrehistoryErrorCount: payload.oldPrehistoryErrorCount,
    missingSunsetDepthCount: payload.missingSunsetDepthCount,
    sunsetDepressionDeg: expectedDep,
    statusCounts: payload.statusCounts,
    reasonCounts: payload.reasonCounts,
    threeStarFound: payload.result?.found ?? null,
    threeStarReason: payload.result?.reason ?? null,
    eventTime: payload.result?.eventTime ?? null,
    minutesAfterSunset: payload.result?.minutesAfterSunset ?? null,
    stars: payload.result?.stars?.map(s => ({ name: s.name, catalogId: s.catalogId, completing: s.completing, effectiveMagnitude: s.effectiveMagnitude })) ?? [],
    earliestSupportedRows: payload.earliestSupportedRows,
  }));
} finally {
  await browser.close();
}

import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = Object.freeze({
  tishrei: Object.freeze({ date: '2025-09-23', sunsetMs: 1758641660932, expectedAod550: 0.22, baselineTau30Minutes: 41.015625 }),
  tammuz: Object.freeze({ date: '2026-06-16', sunsetMs: 1781628380546, expectedAod550: 0.18, baselineTau30Minutes: 49.921875 }),
});
const TAUS = Object.freeze([20, 30, 45, 60]);
const caseId = process.env.CASE_ID;
const tauSeconds = Number(process.env.TAU_SECONDS);
const frozen = CASES[caseId];
if (!frozen) throw new Error(`unknown CASE_ID ${caseId}`);
if (!TAUS.includes(tauSeconds)) throw new Error(`unsupported TAU_SECONDS ${tauSeconds}`);

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async ({ caseId, tauSeconds, frozen }) => {
    const spec = Object.freeze({
      latitudeDeg: 31.778,
      longitudeDeg: 35.235,
      observerElevationM: 800,
      date: frozen.date,
      timeZone: 'Asia/Jerusalem',
      threshold: 1.7,
      requiredCount: 3,
      stabilityMs: 60000,
      scanStepMs: 30000,
      transientScanStepDeg: 0.10,
      fieldFactor: 3.14,
    });
    const set = (id, v) => {
      const e = document.getElementById(id);
      if (!e) throw new Error(`missing #${id}`);
      e.value = String(v);
      e.dispatchEvent(new Event('input', { bubbles: true }));
      e.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg);
    set('lon', spec.longitudeDeg);
    set('date', spec.date);
    set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium');
    set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', 'effective');
    set('threeStarMagnitudeThreshold', spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = 'level-b-v3-crumey-blackwell-equilibrium';
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    const rawCount = Array.isArray(globalThis.__STARS_BUILT_IN_STARS__) ? globalThis.__STARS_BUILT_IN_STARS__.length : -1;
    if (rawCount !== 9090) throw new Error(`raw catalog ${rawCount}`);

    const input = {
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.date,
      timeZone: spec.timeZone,
    };
    const hooks = eval('__levelBSitewideGeometryHooks')(input, Number(frozen.sunsetMs));
    const directSunAltitudeAtSunsetDeg = Number(eval('sunAltitude')(Number(frozen.sunsetMs), spec.latitudeDeg, spec.longitudeDeg));
    const sunsetDepressionDeg = -directSunAltitudeAtSunsetDeg;
    if (!(sunsetDepressionDeg > 0.82 && sunsetDepressionDeg < 0.85)) throw new Error(`sunset depression drift ${sunsetDepressionDeg}`);

    const adapter = await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver = await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const transientModule = await import('/scientific-tools/visibility-v3/level-b-transient-contiguous-support.mjs');
    const adaptationModule = await import('/scientific-tools/visibility-v3/transient-adaptation.mjs');
    if (adaptationModule.DEFAULT_TRANSIENT_ADAPTATION_TAU_SECONDS !== 30) throw new Error('default tau drift');
    if (JSON.stringify([...adaptationModule.TRANSIENT_ADAPTATION_SENSITIVITY_TAU_SECONDS]) !== JSON.stringify([20,30,45,60])) throw new Error('tau sensitivity set drift');

    const runtimeData = await adapter.loadValidatedV3RuntimeData({ fetchImpl: globalThis.fetch });
    const referenceTimeMs = hooks.timeAtSunDepression(6.0);
    const atmosphereResolution = await resolver.resolvePreviewLevelBAtmosphere({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      validTimeMs: referenceTimeMs,
      fetchImpl: globalThis.fetch,
    });
    if (atmosphereResolution.status !== 'RESOLVED') throw new Error(`atmosphere ${atmosphereResolution.status}`);
    if (Math.abs(Number(atmosphereResolution.atmosphere?.aod550) - Number(frozen.expectedAod550)) > 1e-12) {
      throw new Error(`AOD changed ${atmosphereResolution.atmosphere?.aod550} vs ${frozen.expectedAod550}`);
    }

    // Obtain the exact date-transformed 7,653-row catalog through the same application scaffold,
    // but use equilibrium mode only for this catalog handoff; tau science is evaluated below directly.
    delete globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const snapshot = globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    if (!Array.isArray(snapshot) || snapshot.length !== 7653) throw new Error(`transformed-row snapshot ${snapshot?.length}`);
    const rows = snapshot.map(r => ({ ...r }));
    if (globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__ !== undefined) throw new Error('catalog handoff leaked');

    const catalogId = row => row?.isPlanet
      ? (row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`)
      : row?.hip != null && row.hip !== '' ? `HIP ${row.hip}`
        : row?.hr != null && row.hr !== '' ? `HR ${row.hr}`
          : row?.hd != null && row.hd !== '' ? `HD ${row.hd}`
            : (row?.name ?? row?.id ?? 'target');
    const candidates = rows
      .map(row => ({ key: catalogId(row), row, target: engine.normalizeSitewideTarget(row) }))
      .filter(entry => entry.target);

    const evaluated = [];
    const statusCounts = {};
    const reasonCounts = {};
    for (let i = 0; i < candidates.length; i += 1) {
      const entry = candidates[i];
      const result = await transientModule.evaluateLevelBTransientWithContiguousSupport({
        runtimeData,
        target: entry.target,
        observerElevationM: spec.observerElevationM,
        sunsetMs: Number(frozen.sunsetMs),
        sunDepressionAtSunsetDeg: sunsetDepressionDeg,
        geometryAtSunDepression: hooks.geometryAtSunDepression,
        timeAtSunDepression: hooks.timeAtSunDepression,
        atmosphereResolution,
        scanStepDeg: spec.transientScanStepDeg,
        transientTauSeconds: tauSeconds,
      });
      const status = result?.status ?? 'UNKNOWN';
      const reason = result?.reason ?? null;
      statusCounts[status] = (statusCounts[status] || 0) + 1;
      if (reason) reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
      const intervalsMs = engine.visibilityIntervalsToMs(result?.timeline, hooks.timeAtSunDepression);
      evaluated.push({ ...entry, result, intervalsMs });
      if ((i + 1) % 500 === 0) console.log(`TAU_PROGRESS ${caseId} tau=${tauSeconds} ${i + 1}/${candidates.length}`);
    }

    const depressionAt = t => -Number(eval('sunAltitude')(t, spec.latitudeDeg, spec.longitudeDeg));
    const point = engine.createSitewidePointEvaluator({
      runtimeData,
      atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const qualifierCache = new Map();
    const qualifiesEffectiveAt = (entry, t) => {
      const key = `${entry.key}|${Number(t).toFixed(3)}`;
      if (qualifierCache.has(key)) return qualifierCache.get(key);
      const d = depressionAt(t);
      let pass = false;
      if (Number.isFinite(d) && d >= 2 && d <= 10.5) {
        const sample = point(entry.target, d);
        const apparent = Number(sample?.stellar?.apparentVMagAtEye);
        pass = sample?.status === 'SUPPORTED' && Number.isFinite(apparent) && apparent >= spec.threshold - 1e-10;
      }
      qualifierCache.set(key, pass);
      return pass;
    };
    const endMs = hooks.timeAtSunDepression(10.5);
    const event = engine.findStableSimultaneousVisibilityEventWithQualifier(evaluated, {
      requiredCount: spec.requiredCount,
      stabilityMs: spec.stabilityMs,
      startMs: Number(frozen.sunsetMs),
      endMs,
      scanStepMs: spec.scanStepMs,
      qualifiesAt: qualifiesEffectiveAt,
    });

    const selected = event.found ? event.selected.map(entry => {
      const d = depressionAt(event.eventTimeMs);
      const sample = point(entry.target, d);
      return {
        key: entry.key,
        name: entry.row?.name,
        catalogMagnitude: Number(entry.row?.mag),
        apparentVMagAtEye: Number(sample?.stellar?.apparentVMagAtEye),
        transientFirstVisibleTimeMs: entry.result?.firstVisibleTimeMs ?? null,
        transientMinutesAfterSunset: entry.result?.minutesAfterSunset ?? null,
        transientVisibilityMarginAtOwnFirstEventMag: entry.result?.visibilityMarginMag ?? null,
        transientAdaptationPenaltyAtOwnFirstEventMag: entry.result?.transientAdaptationPenaltyMag ?? null,
        transientTauSeconds: entry.result?.transientTauSeconds ?? null,
        geometryAtThreeStarEvent: hooks.geometryAtSunDepression(d, entry.target),
        completing: event.completingKeys?.includes(entry.key) ?? false,
      };
    }) : [];

    const result = {
      found: event.found,
      eventTimeMs: event.found ? event.eventTimeMs : null,
      minutesAfterSunset: event.found ? (event.eventTimeMs - Number(frozen.sunsetMs)) / 60000 : null,
      sunDepressionDeg: event.found ? depressionAt(event.eventTimeMs) : null,
      visibleCount: event.visibleCount,
      completingKeys: event.completingKeys ?? [],
      selected,
    };
    if (tauSeconds === 30) {
      if (!result.found) throw new Error('tau30 baseline event missing');
      if (Math.abs(result.minutesAfterSunset - frozen.baselineTau30Minutes) > 0.02) {
        throw new Error(`tau30 baseline drift ${result.minutesAfterSunset} vs ${frozen.baselineTau30Minutes}`);
      }
    }
    return {
      caseId,
      tauSeconds,
      spec,
      frozen,
      rawCatalogCount: rawCount,
      directCatalogRowCount: rows.length,
      normalizedCandidateCount: candidates.length,
      atmosphereResolution,
      sunsetDepressionDeg,
      statusCounts,
      reasonCounts,
      entriesWithVisibilityIntervals: evaluated.filter(e => e.intervalsMs.length).length,
      qualifierCacheSize: qualifierCache.size,
      result,
    };
  }, { caseId, tauSeconds, frozen });

  const outDir = path.join(process.env.RUNNER_TEMP, 'jerusalem-transient-tau-sensitivity');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, `${caseId}-tau-${tauSeconds}.json`), JSON.stringify({
    schemaVersion: 1,
    status: 'JERUSALEM_TRANSIENT_TAU_SENSITIVITY_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    audit,
    browserConsole,
    claimBoundary: {
      sensitivityOnly: true,
      defaultTau30Unchanged: true,
      fieldFactor314Unchanged: true,
      noTauCalibrationClaim: true,
      noHumanFirstSeeingValidation: true,
      noParameterTuning: true,
      noMYSTIC: true,
      noProductionChange: true,
      noPandora: true,
    },
  }, null, 2) + '\n');
  console.log('TAU_SENSITIVITY=' + JSON.stringify({ caseId, tauSeconds, result: audit.result, statusCounts: audit.statusCounts }));
} finally {
  await browser.close();
}

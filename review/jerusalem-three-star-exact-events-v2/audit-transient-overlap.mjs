import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  'tishrei-transient-overlap': {
    civilDate: '2025-09-23',
    sunsetMs: 1758641660932,
    equilibriumEventTimeMs: 1758642904994.5,
    equilibriumKeys: ['HR 6134', 'HR 6556', 'HR 7796'],
  },
  'tammuz-transient-overlap': {
    civilDate: '2026-06-16',
    sunsetMs: 1781628380546,
    equilibriumEventTimeMs: 1781629701483.5,
    equilibriumKeys: ['HR 5191', 'HR 4905', 'HR 3982'],
  },
};

const label = process.env.CASE_LABEL;
const frozen = CASES[label];
if (!frozen) throw new Error(`unknown CASE_LABEL ${label}`);
const spec = Object.freeze({
  label,
  civilDate: frozen.civilDate,
  sunsetMs: frozen.sunsetMs,
  engineMode: 'level-b-v3-crumey-blackwell-transient-experimental',
  latitudeDeg: 31.778,
  longitudeDeg: 35.235,
  observerElevationM: 800,
  timeZone: 'Asia/Jerusalem',
  effectiveThreshold: 1.7,
  requiredCount: 3,
  stabilityMs: 60_000,
  scanStepMs: 30_000,
  equilibriumEventTimeMs: frozen.equilibriumEventTimeMs,
  equilibriumKeys: frozen.equilibriumKeys,
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async spec => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg); set('lon', spec.longitudeDeg); set('date', spec.civilDate);
    set('timezone', spec.timeZone); set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode); set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', 'effective'); set('threeStarMagnitudeThreshold', spec.effectiveThreshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');

    const catalog = globalThis.__STARS_BUILT_IN_STARS__;
    if (!Array.isArray(catalog) || catalog.length !== 9090) throw new Error(`catalog count ${catalog?.length}`);
    const canRise = eval('canGeometricallyRise');
    const rows = catalog.filter(s => canRise(s, spec.latitudeDeg)).map(s => ({ ...s }));
    const catalogId = row => {
      if (row?.isPlanet) return row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`;
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };

    const sunsetMs = Number(spec.sunsetMs);
    if (!Number.isFinite(sunsetMs)) throw new Error(`invalid frozen sunset ${sunsetMs}`);
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, sunsetMs);
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const evaluation = await engine.evaluateSitewideRows({
      rows,
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      sunsetMs,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
      timeAtSunDepression: hooks.timeAtSunDepression,
      engineMode: spec.engineMode,
      fetchImpl: globalThis.fetch,
    });
    if (evaluation.status !== 'COMPLETE') throw new Error(`evaluation ${evaluation.status}`);

    const entries = evaluation.results.filter(x => x.target).map(x => ({
      key: catalogId(x.row), row: x.row, target: x.target, result: x.result, intervalsMs: x.intervalsMs,
    }));
    const intervalEntries = entries.filter(x => x.intervalsMs.length > 0);
    const statusCounts = {};
    const reasonCounts = {};
    for (const e of entries) {
      const status = e.result?.status ?? 'NULL';
      const reason = e.result?.reason ?? 'NULL';
      statusCounts[status] = (statusCounts[status] ?? 0) + 1;
      reasonCounts[reason] = (reasonCounts[reason] ?? 0) + 1;
    }

    const point = engine.createSitewidePointEvaluator({
      runtimeData: evaluation.runtimeData,
      atmosphereResolution: evaluation.atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const sunAltitudeFn = eval('sunAltitude');
    const depressionAt = t => -Number(sunAltitudeFn(t, spec.latitudeDeg, spec.longitudeDeg));
    const pointCache = new Map();
    const pointSample = (entry, t) => {
      const dep = depressionAt(t);
      if (!Number.isFinite(dep) || dep < 2 || dep > 10.5) return null;
      const k = `${entry.key}|${Math.round(t / 250)}`;
      if (!pointCache.has(k)) pointCache.set(k, point(entry.target, dep));
      return pointCache.get(k);
    };
    const qualifiesAt = (entry, t) => {
      const s = pointSample(entry, t);
      const apparent = Number(s?.stellar?.apparentVMagAtEye);
      return s?.status === 'SUPPORTED' && Number.isFinite(apparent) && apparent >= spec.effectiveThreshold - 1e-10;
    };
    const intervalContains = (entry, t) => entry.intervalsMs.some(i => t + 1 >= i.startMs && t - 1 <= i.endMs);
    const stableAt = t => {
      const times = [t, t + spec.stabilityMs / 2, t + spec.stabilityMs];
      return intervalEntries.filter(e => times.every(x => intervalContains(e, x) && qualifiesAt(e, x)));
    };
    const startMs = Number(hooks.timeAtSunDepression(2.0));
    const endMs = Number(hooks.timeAtSunDepression(10.5));
    if (![startMs, endMs].every(Number.isFinite)) throw new Error('invalid frozen-domain times');
    let maxStableCount = -1;
    let maxStableTimeMs = null;
    let maxStableKeys = [];
    let positiveStableSamples = 0;
    for (let t = startMs; t <= endMs - spec.stabilityMs + 1; t += spec.scanStepMs) {
      const stable = stableAt(t);
      if (stable.length > 0) positiveStableSamples += 1;
      if (stable.length > maxStableCount) {
        maxStableCount = stable.length;
        maxStableTimeMs = t;
        maxStableKeys = stable.map(e => e.key);
      }
    }
    const exactEvent = engine.findStableSimultaneousVisibilityEventWithQualifier(entries, {
      requiredCount: spec.requiredCount,
      stabilityMs: spec.stabilityMs,
      startMs,
      endMs,
      scanStepMs: spec.scanStepMs,
      qualifiesAt,
    });

    const byKey = new Map(entries.map(e => [e.key, e]));
    const compactPoint = (entry, t) => {
      const s = pointSample(entry, t);
      return {
        timestampMs: t,
        sunDepressionDeg: depressionAt(t),
        status: s?.status ?? null,
        apparentVMagAtEye: s?.stellar?.apparentVMagAtEye ?? null,
        equilibriumVisibilityMarginMag: s?.visibility?.visibilityMarginMag ?? null,
        limitingVMagnitude: s?.visibility?.limitingVMagnitude ?? null,
        geometry: s?.geometry ?? null,
        support: s?.support ?? null,
      };
    };
    const equilibriumTripleTransient = spec.equilibriumKeys.map(key => {
      const e = byKey.get(key);
      if (!e) return { key, missing: true };
      const r = e.result ?? {};
      return {
        key,
        name: e.row?.name ?? null,
        catalogMagnitude: e.row?.magOriginal ?? e.row?.mag ?? null,
        status: r.status ?? null,
        reason: r.reason ?? null,
        firstVisibleTimeMs: r.firstVisibleTimeMs ?? null,
        firstVisibleSunDepressionDeg: r.sunDepressionDeg ?? null,
        minutesAfterSunset: r.minutesAfterSunset ?? null,
        transientAdaptationPenaltyMagAtFirstVisible: r.transientAdaptationPenaltyMag ?? null,
        transientTauSeconds: r.transientTauSeconds ?? null,
        transientAdaptationValidationTier: r.transientAdaptationValidationTier ?? null,
        transientSupportAudit: r.transientSupportAudit ?? null,
        timeline: r.timeline ?? null,
        intervalsMs: e.intervalsMs,
        pointAtEquilibriumEvent: compactPoint(e, spec.equilibriumEventTimeMs),
        intervalVisibleAtEquilibriumEvent: intervalContains(e, spec.equilibriumEventTimeMs),
        effectiveQualifiedAtEquilibriumEvent: qualifiesAt(e, spec.equilibriumEventTimeMs),
      };
    });

    const topFirstIntervals = intervalEntries
      .map(e => ({ key: e.key, name: e.row?.name ?? null, startMs: e.intervalsMs[0].startMs, startSunDepressionDeg: e.intervalsMs[0].startSunDepressionDeg, endMs: e.intervalsMs[0].endMs, endSunDepressionDeg: e.intervalsMs[0].endSunDepressionDeg, status: e.result?.status ?? null, adaptationPenaltyMag: e.result?.transientAdaptationPenaltyMag ?? null }))
      .sort((a,b) => a.startMs - b.startMs)
      .slice(0, 30);

    return {
      catalogCount: catalog.length,
      evaluatedTargetCount: entries.length,
      intervalCandidateCount: intervalEntries.length,
      statusCounts,
      reasonCounts,
      atmosphereResolution: evaluation.atmosphereResolution,
      frozenDomain: { startMs, endMs },
      exactEvent,
      maxStableCount,
      maxStableTimeMs,
      maxStableSunDepressionDeg: maxStableTimeMs == null ? null : depressionAt(maxStableTimeMs),
      maxStableKeys,
      positiveStableSamples,
      equilibriumTripleTransient,
      topFirstIntervals,
    };
  }, spec);

  const outDir = path.join(process.env.RUNNER_TEMP, 'transient-overlap-audit');
  fs.mkdirSync(outDir, { recursive: true });
  const payload = {
    schemaVersion: 1,
    status: 'JERUSALEM_TRANSIENT_OVERLAP_DIAGNOSTIC_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    preregisteredCase: spec,
    audit,
    claimBoundary: { diagnosticOnly: true, transientExperimental: true, noTuning: true, F314Unchanged: true, noMYSTIC: true, noPandora: true, humanFirstSeeingValidated: false },
    browserConsole,
  };
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(payload, null, 2) + '\n');
  console.log('TRANSIENT_OVERLAP_AUDIT=' + JSON.stringify({
    label,
    evaluatedTargetCount: audit.evaluatedTargetCount,
    intervalCandidateCount: audit.intervalCandidateCount,
    exactEvent: audit.exactEvent,
    maxStableCount: audit.maxStableCount,
    maxStableSunDepressionDeg: audit.maxStableSunDepressionDeg,
    maxStableKeys: audit.maxStableKeys,
    statusCounts: audit.statusCounts,
    reasonCounts: audit.reasonCounts,
    equilibriumTripleTransient: audit.equilibriumTripleTransient,
  }));
} finally {
  await browser.close();
}

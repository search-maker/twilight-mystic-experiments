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

  const result = await page.evaluate(async () => {
    const spec = {
      latitudeDeg: 31.778,
      longitudeDeg: 35.235,
      observerElevationM: 800,
      date: '2026-06-16',
      timeZone: 'Asia/Jerusalem',
      engineMode: 'level-b-v3-crumey-blackwell-equilibrium',
      threshold: 1.7,
      requiredCount: 3,
    };
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
    set('date', spec.date);
    set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode);
    set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', 'effective');
    set('threeStarMagnitudeThreshold', spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');

    // First run the exact UI scaffold once for an external comparison only.
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui = JSON.parse(JSON.stringify(eval('threeStarResultData')));

    const catalogAll = globalThis.__STARS_BUILT_IN_STARS__;
    if (!Array.isArray(catalogAll) || catalogAll.length !== 9090) throw new Error(`catalog ${catalogAll?.length}`);
    const canRise = eval('canGeometricallyRise');
    const rows = catalogAll.filter(star => canRise(star, spec.latitudeDeg)).map(star => ({ ...star }));
    if (rows.length < 7000) throw new Error(`unexpected filtered rows ${rows.length}`);

    const sunsetMs = Number(ui.sunsetTime);
    if (!Number.isFinite(sunsetMs)) throw new Error('UI sunset missing');
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.date,
      timeZone: spec.timeZone,
    }, sunsetMs);
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');

    // ONE evaluation / ONE atmosphere object feeds the point evaluator, event solver,
    // selected-star point samples, and interval comparison below.
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

    const catalogId = row => {
      if (row?.isPlanet) return row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`;
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };
    const candidates = evaluation.results.filter(entry => entry.target).map(entry => ({
      key: catalogId(entry.row),
      row: entry.row,
      target: entry.target,
      intervalsMs: entry.intervalsMs ?? [],
      result: entry.result,
    }));
    const point = engine.createSitewidePointEvaluator({
      runtimeData: evaluation.runtimeData,
      atmosphereResolution: evaluation.atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const depressionAt = timestampMs => -Number(eval('sunAltitude')(timestampMs, spec.latitudeDeg, spec.longitudeDeg));
    const pointCache = new Map();
    const sampleAt = (entry, timestampMs) => {
      const key = `${entry.key}|${Number(timestampMs).toFixed(3)}`;
      if (!pointCache.has(key)) pointCache.set(key, point(entry.target, depressionAt(timestampMs)));
      return pointCache.get(key);
    };
    const qualifiesAt = (entry, timestampMs) => {
      const d = depressionAt(timestampMs);
      if (!Number.isFinite(d) || d < 2 || d > 10.5) return false;
      const sample = sampleAt(entry, timestampMs);
      return sample?.status === 'SUPPORTED'
        && Number(sample?.visibility?.visibilityMarginMag) >= -1e-10
        && Number(sample?.stellar?.apparentVMagAtEye) >= spec.threshold - 1e-10;
    };
    const endMs = hooks.timeAtSunDepression(10.5) ?? sunsetMs + 8 * 3600e3;
    const event = engine.findStableSimultaneousQualifiedEvent(candidates, {
      requiredCount: spec.requiredCount,
      stabilityMs: 60_000,
      startMs: sunsetMs,
      endMs,
      scanStepMs: 30_000,
      qualifiesAt,
    });
    if (!event.found) throw new Error('single-evaluation solver found no Tammuz event');

    const selected = event.selected.map(entry => {
      const at = t => {
        const sample = sampleAt(entry, t);
        return {
          timestampMs: t,
          sunDepressionDeg: depressionAt(t),
          qualifies: qualifiesAt(entry, t),
          status: sample?.status,
          visibilityMarginMag: sample?.visibility?.visibilityMarginMag,
          apparentVMagAtEye: sample?.stellar?.apparentVMagAtEye,
          limitingVMagnitude: sample?.visibility?.limitingVMagnitude,
        };
      };
      return {
        key: entry.key,
        name: entry.row?.name,
        firstQualifyingTime: entry.firstVisibleTime,
        timelineIntervalsMs: entry.intervalsMs,
        eventGeometry: hooks.geometryAtSunDepression(depressionAt(event.eventTimeMs), entry.target),
        event: at(event.eventTimeMs),
        plus30: at(event.eventTimeMs + 30_000),
        plus60: at(event.eventTimeMs + 60_000),
      };
    });
    const regulus = candidates.find(entry => entry.key === 'HR 3982' || /Regulus/i.test(String(entry.row?.name)));
    const regulusAudit = regulus ? {
      timelineIntervalsMs: regulus.intervalsMs,
      atUiEvent: Number.isFinite(Number(ui.eventTime)) ? {
        timestampMs: Number(ui.eventTime),
        sunDepressionDeg: depressionAt(Number(ui.eventTime)),
        qualifies: qualifiesAt(regulus, Number(ui.eventTime)),
        sample: sampleAt(regulus, Number(ui.eventTime)),
      } : null,
      atSingleEvent: {
        timestampMs: event.eventTimeMs,
        sunDepressionDeg: depressionAt(event.eventTimeMs),
        qualifies: qualifiesAt(regulus, event.eventTimeMs),
        sample: sampleAt(regulus, event.eventTimeMs),
      },
    } : null;

    return {
      spec,
      ui,
      rowsCount: rows.length,
      atmosphereResolution: evaluation.atmosphereResolution,
      event,
      selected,
      regulusAudit,
      uiMinusSingleEventMs: Number(ui.eventTime) - Number(event.eventTimeMs),
    };
  });

  const selectedBad = result.selected.filter(s => !s.event.qualifies || !s.plus30.qualifies || !s.plus60.qualifies);
  if (selectedBad.length) throw new Error(`Solver self-consistency failure: ${JSON.stringify(selectedBad)}`);
  const outDir = path.join(process.env.RUNNER_TEMP, 'tammuz-single-evaluation-audit');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify({
    schemaVersion: 1,
    status: 'TAMMUZ_SINGLE_EVALUATION_AUDIT_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    result,
    browserConsole: consoleLines,
    claimBoundary: { diagnosticOnly: true, noTuning: true, F314Unchanged: true, noMYSTIC: true, noPandora: true },
  }, null, 2) + '\n');
  console.log('TAMMUZ_SINGLE_EVAL=' + JSON.stringify({
    uiEvent: result.ui?.eventTime,
    singleEvent: result.event?.eventTimeMs,
    deltaMs: result.uiMinusSingleEventMs,
    atmosphere: result.atmosphereResolution,
    selected: result.selected,
    regulusAudit: result.regulusAudit,
  }));
} finally {
  await browser.close();
}

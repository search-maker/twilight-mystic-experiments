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
    const spec = {
      latitudeDeg: 31.778,
      longitudeDeg: 35.235,
      observerElevationM: 800,
      date: '2026-03-19',
      timeZone: 'Asia/Jerusalem',
      engineMode: 'level-b-v3-crumey-blackwell-equilibrium',
      threshold: 1.7,
      requiredCount: 3,
      stabilityMs: 60_000,
      scanStepMs: 30_000,
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
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui = JSON.parse(JSON.stringify(eval('threeStarResultData')));
    if (ui?.found !== false || ui?.reason !== 'NO_STABLE_SIMULTANEOUS_LEVEL_B_EVENT_IN_FROZEN_DOMAIN') {
      throw new Error(`Expected frozen Nisan no-event, got ${JSON.stringify({found:ui?.found, reason:ui?.reason})}`);
    }

    const catalogAll = globalThis.__STARS_BUILT_IN_STARS__;
    const canRise = eval('canGeometricallyRise');
    const rows = catalogAll.filter(star => canRise(star, spec.latitudeDeg)).map(star => ({ ...star }));
    const sunsetMs = Number(ui.sunsetTime);
    const input = { latitudeDeg:spec.latitudeDeg, longitudeDeg:spec.longitudeDeg, observerElevationM:spec.observerElevationM, date:spec.date, timeZone:spec.timeZone };
    const hooks = eval('__levelBSitewideGeometryHooks')(input, sunsetMs);
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
    const point = engine.createSitewidePointEvaluator({
      runtimeData: evaluation.runtimeData,
      atmosphereResolution: evaluation.atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const entries = evaluation.results.filter(e => e.target).map(e => ({ row:e.row, target:e.target }));
    const catalogId = row => row?.hip != null && row.hip !== '' ? `HIP ${row.hip}` : row?.hr != null && row.hr !== '' ? `HR ${row.hr}` : row?.hd != null && row.hd !== '' ? `HD ${row.hd}` : (row?.name ?? row?.id ?? 'target');
    const depressionAt = t => -Number(eval('sunAltitude')(t, spec.latitudeDeg, spec.longitudeDeg));
    const endMs = hooks.timeAtSunDepression(10.5);
    if (!Number.isFinite(endMs)) throw new Error('10.5 degree time unavailable');

    const cache = new Map();
    const samplesAt = timestampMs => {
      const cacheKey = Number(timestampMs).toFixed(3);
      if (cache.has(cacheKey)) return cache.get(cacheKey);
      const depression = depressionAt(timestampMs);
      const rowsAt = entries.map(entry => {
        const sample = depression >= 2 && depression <= 10.5 ? point(entry.target, depression) : null;
        const supported = sample?.status === 'SUPPORTED';
        const margin = Number(sample?.visibility?.visibilityMarginMag);
        const apparent = Number(sample?.stellar?.apparentVMagAtEye);
        const physicallyVisible = supported && Number.isFinite(margin) && margin >= -1e-10;
        const effectivePass = supported && Number.isFinite(apparent) && apparent >= spec.threshold - 1e-10;
        return { entry, sample, supported, margin, apparent, physicallyVisible, effectivePass, qualifies: physicallyVisible && effectivePass };
      });
      cache.set(cacheKey, { timestampMs, depression, rowsAt });
      return cache.get(cacheKey);
    };
    const countQualifying = t => samplesAt(t).rowsAt.reduce((n,r) => n + (r.qualifies ? 1 : 0), 0);
    const stableCount = t => {
      const a = samplesAt(t).rowsAt;
      const b = samplesAt(t + spec.stabilityMs/2).rowsAt;
      const c = samplesAt(t + spec.stabilityMs).rowsAt;
      let n = 0;
      for (let i=0;i<a.length;i++) if (a[i].qualifies && b[i].qualifies && c[i].qualifies) n++;
      return n;
    };

    const coarse = [];
    for (let t = hooks.timeAtSunDepression(2); t <= endMs - spec.stabilityMs; t += spec.scanStepMs) {
      coarse.push({ timestampMs:t, sunDepressionDeg:depressionAt(t), instantaneousCount:countQualifying(t), stable60sCount:stableCount(t) });
    }
    const maxInstant = Math.max(...coarse.map(r => r.instantaneousCount));
    const maxStable = Math.max(...coarse.map(r => r.stable60sCount));
    const bestCoarse = coarse.filter(r => r.instantaneousCount === maxInstant).sort((a,b) => a.timestampMs-b.timestampMs)[0];

    // Refine +/- 60 seconds around the first best coarse sample at 2-second resolution.
    const refine = [];
    for (let t = Math.max(hooks.timeAtSunDepression(2), bestCoarse.timestampMs-60_000); t <= Math.min(endMs-spec.stabilityMs, bestCoarse.timestampMs+60_000); t += 2_000) {
      refine.push({ timestampMs:t, sunDepressionDeg:depressionAt(t), instantaneousCount:countQualifying(t), stable60sCount:stableCount(t) });
    }
    const best = refine.slice().sort((a,b) => (b.stable60sCount-a.stable60sCount) || (b.instantaneousCount-a.instantaneousCount) || (a.timestampMs-b.timestampMs))[0];
    const bestSamples = samplesAt(best.timestampMs).rowsAt;
    const qualifying = bestSamples.filter(r => r.qualifies).sort((a,b) => b.margin-a.margin);
    const effectiveButInvisible = bestSamples.filter(r => r.effectivePass && !r.physicallyVisible).sort((a,b) => b.margin-a.margin).slice(0,12);
    const visibleButTooBright = bestSamples.filter(r => r.physicallyVisible && !r.effectivePass).sort((a,b) => b.apparent-a.apparent).slice(0,12);
    const compact = r => ({
      name:r.entry.row?.name,
      catalogId:catalogId(r.entry.row),
      catalogMagnitude:Number(r.entry.row?.mag),
      status:r.sample?.status,
      visibilityMarginMag:r.margin,
      apparentVMagAtEye:r.apparent,
      limitingVMagnitude:r.sample?.visibility?.limitingVMagnitude,
      targetAltitudeDeg:r.sample?.geometry?.targetAltitudeDeg,
      relativeAzimuthDeg:r.sample?.geometry?.relativeAzimuthDeg,
    });

    return {
      spec,
      ui,
      rowsCount:rows.length,
      atmosphereResolution:evaluation.atmosphereResolution,
      coarse,
      maxima:{ maxInstantaneousCount:maxInstant, maxStable60sCount:maxStable, best },
      atBest:{ qualifying:qualifying.slice(0,12).map(compact), effectiveButInvisible:effectiveButInvisible.map(compact), visibleButTooBright:visibleButTooBright.map(compact) },
    };
  });

  const outDir = path.join(process.env.RUNNER_TEMP, 'nisan-no-event-audit');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify({
    schemaVersion:1,
    status:'NISAN_NO_EVENT_BLOCKER_DIAGNOSTIC_COMPLETE',
    applicationSha:process.env.APPLICATION_SHA,
    audit,
    browserConsole:consoleLines,
    claimBoundary:{ diagnosticOnly:true, noTuning:true, F314Unchanged:true, noMYSTIC:true, noPandora:true },
  }, null, 2)+'\n');
  console.log('NISAN_BLOCKER=' + JSON.stringify({ atmosphere:audit.atmosphereResolution, maxima:audit.maxima, atBest:audit.atBest }));
} finally {
  await browser.close();
}

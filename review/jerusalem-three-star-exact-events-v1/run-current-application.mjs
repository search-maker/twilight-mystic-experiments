import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const env = process.env;
const spec = Object.freeze({
  label: env.CASE_LABEL,
  civilDate: env.CASE_DATE,
  hebrewLabel: env.HEBREW_LABEL,
  engineMode: env.ENGINE_MODE,
  latitudeDeg: Number(env.LATITUDE_DEG),
  longitudeDeg: Number(env.LONGITUDE_DEG),
  observerElevationM: Number(env.OBSERVER_ELEVATION_M),
  timeZone: env.TIME_ZONE,
  magnitudeBasis: env.MAGNITUDE_BASIS,
  magnitudeThreshold: Number(env.MAGNITUDE_THRESHOLD),
  requiredCount: Number(env.REQUIRED_COUNT),
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', (m) => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const controls = await page.evaluate(async (spec) => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return el.value;
    };
    const select = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      const opts = Array.from(el.options || []).map((o) => o.value);
      if (opts.length && !opts.includes(String(value))) throw new Error(`#${id} has no ${value}; options=${opts.join(',')}`);
      return set(id, value);
    };
    try { localStorage.clear(); } catch (_) {}
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = true;
    if (document.getElementById('calculatorFeature')) set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg);
    set('lon', spec.longitudeDeg);
    set('date', spec.civilDate);
    if (document.getElementById('timezone')) set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    select('visibilityEngineMode', spec.engineMode);
    select('threeStarCount', spec.requiredCount);
    select('threeStarMagnitudeBasis', spec.magnitudeBasis);
    set('threeStarMagnitudeThreshold', spec.magnitudeThreshold);
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    const out = {
      calculatorFeature: document.getElementById('calculatorFeature')?.value ?? null,
      latitudeDeg: Number(document.getElementById('lat')?.value),
      longitudeDeg: Number(document.getElementById('lon')?.value),
      civilDate: document.getElementById('date')?.value ?? null,
      timeZone: document.getElementById('timezone')?.value ?? null,
      observerElevationM: Number(document.getElementById('observerElevationM')?.value),
      visibilityEngineMode: document.getElementById('visibilityEngineMode')?.value ?? globalThis.__STAR_VISIBILITY_ENGINE_MODE__,
      threeStarCount: Number(document.getElementById('threeStarCount')?.value),
      magnitudeBasis: document.getElementById('threeStarMagnitudeBasis')?.value ?? null,
      magnitudeThreshold: Number(document.getElementById('threeStarMagnitudeThreshold')?.value),
      catalogCount: globalThis.__STARS_BUILT_IN_STARS__?.length ?? null,
    };
    if (out.catalogCount !== 9090) throw new Error(`catalog count ${out.catalogCount}`);
    return out;
  }, spec);

  const ui = await page.evaluate(async () => {
    await eval('calculate()');
    return { result: eval('threeStarResultData'), skyMap: eval('threeStarSkyMapData') };
  });

  const detailed = await page.evaluate(async ({ spec, ui }) => {
    const result = ui.result;
    if (!result || typeof result !== 'object') throw new Error('no threeStarResultData');
    if (!result.found) return { found: false, reason: result.reason ?? null, result };
    const catalog = globalThis.__STARS_BUILT_IN_STARS__;
    const catalogId = (row) => {
      if (row?.isPlanet) return row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`;
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };
    const rows = result.stars.map((star) => {
      const row = catalog.find((r) => catalogId(r) === star.catalogId) || catalog.find((r) => r.name === star.name);
      if (!row) throw new Error(`row missing ${star.catalogId}/${star.name}`);
      return row;
    });
    const sunsetMs = Number(result.sunsetTime);
    if (!Number.isFinite(sunsetMs)) throw new Error(`sunsetTime invalid ${result.sunsetTime}`);
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
    if (evaluation.status !== 'COMPLETE') return {
      found: true,
      result,
      detailedEvaluationStatus: evaluation.status,
      atmosphereResolution: evaluation.atmosphereResolution,
      rows,
    };
    const eventTimeMs = Number(result.eventTime ?? result.time);
    const sunDepressionDeg = -Number(eval('sunAltitude')(eventTimeMs, spec.latitudeDeg, spec.longitudeDeg));
    const point = engine.createSitewidePointEvaluator({
      runtimeData: evaluation.runtimeData,
      atmosphereResolution: evaluation.atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const byId = new Map(evaluation.results.map((x) => [catalogId(x.row), x]));
    const stars = result.stars.map((star) => {
      const x = byId.get(star.catalogId);
      if (!x) throw new Error(`detail missing ${star.catalogId}`);
      return {
        uiStar: star,
        row: x.row,
        normalizedTarget: x.target,
        intervalsMs: x.intervalsMs,
        timelineResult: x.result,
        eventGeometry: hooks.geometryAtSunDepression(sunDepressionDeg, x.target),
        eventSample: point(x.target, sunDepressionDeg),
      };
    });
    return { found: true, result, sunsetMs, eventTimeMs, sunDepressionDeg, atmosphereResolution: evaluation.atmosphereResolution, stars };
  }, { spec, ui });

  const output = {
    schemaVersion: 3,
    status: 'EXACT_CURRENT_APPLICATION_JERUSALEM_THREE_STAR_DIAGNOSTIC',
    applicationRepo: env.APPLICATION_REPO,
    applicationSha: env.APPLICATION_SHA,
    preregisteredCase: spec,
    exactUiControls: controls,
    uiThreeStarResult: ui.result,
    uiSkyMapResult: ui.skyMap,
    detailed,
    claimBoundary: {
      computationalDiagnosticOnly: true,
      f314ConfiguredCriterionUnchanged: true,
      measuredRealSkyValidated: false,
      humanFirstSeeingValidated: false,
      productionAuthorized: false,
      pandoraOpened: false,
      noTuning: true,
    },
    browserConsole,
  };
  const outPath = path.join(env.RUNNER_TEMP, 'jerusalem-three-star-exact-events', `${spec.label}.json`);
  fs.writeFileSync(outPath, JSON.stringify(output, null, 2) + '\n');
  console.log('JERUSALEM_EXACT_EVENT_SUMMARY=' + JSON.stringify({
    label: spec.label,
    controls,
    found: ui.result?.found ?? null,
    reason: ui.result?.reason ?? null,
    eventTime: ui.result?.eventTime ?? ui.result?.time ?? null,
    sunsetTime: ui.result?.sunsetTime ?? null,
    minutesAfterSunset: ui.result?.minutesAfterSunset ?? null,
    sunAltitude: ui.result?.sunAltitude ?? null,
    detailedSunDepression: detailed?.sunDepressionDeg ?? null,
    atmosphere: detailed?.atmosphereResolution ?? null,
    stars: ui.result?.stars ?? [],
    detailStars: detailed?.stars?.map((s) => ({ name: s.uiStar?.name, catalogId: s.uiStar?.catalogId, intervalsMs: s.intervalsMs, eventGeometry: s.eventGeometry, eventSample: s.eventSample })) ?? [],
  }));
} finally {
  await browser.close();
}

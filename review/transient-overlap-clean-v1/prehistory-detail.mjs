import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  'tishrei-transient-overlap': {
    civilDate: '2025-09-23',
    sunsetMs: 1758641660932,
    equilibriumKeys: ['HR 6134', 'HR 6556', 'HR 7796'],
  },
  'tammuz-transient-overlap': {
    civilDate: '2026-06-16',
    sunsetMs: 1781628380546,
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
  equilibriumKeys: frozen.equilibriumKeys,
  latitudeDeg: 31.778,
  longitudeDeg: 35.235,
  observerElevationM: 800,
  timeZone: 'Asia/Jerusalem',
  engineMode: 'level-b-v3-crumey-blackwell-transient-experimental',
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
    set('lat', spec.latitudeDeg); set('lon', spec.longitudeDeg); set('date', spec.civilDate);
    set('timezone', spec.timeZone); set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');

    const catalog = globalThis.__STARS_BUILT_IN_STARS__;
    if (!Array.isArray(catalog) || catalog.length !== 9090) throw new Error(`catalog count ${catalog?.length}`);
    const catalogId = row => {
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };
    const rows = spec.equilibriumKeys.map(key => {
      const row = catalog.find(x => catalogId(x) === key);
      if (!row) throw new Error(`missing ${key}`);
      return { ...row };
    });
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, spec.sunsetMs);
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const prehistory = await import('/scientific-tools/visibility-v3/sunset-adaptation-prehistory.mjs');
    const transient = await import('/scientific-tools/visibility-v3/transient-adaptation.mjs');
    const evaluation = await engine.evaluateSitewideRows({
      rows,
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      sunsetMs: spec.sunsetMs,
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

    const results = evaluation.results.map(entry => {
      const key = catalogId(entry.row);
      const steps = Math.ceil((10.5 - 2.0) / 0.10);
      const history = [];
      for (let i = 0; i <= steps; i += 1) {
        const depression = i === steps ? 10.5 : 2.0 + i * (8.5 / steps);
        const sample = point(entry.target, depression);
        if (sample?.status !== 'SUPPORTED' || sample?.sky?.channels?.photopic?.available !== true) {
          history.push({ depression, timestampMs: Number(hooks.timeAtSunDepression(depression)), supported: false, status: sample?.status ?? null, reason: sample?.reason ?? null, photopic: null });
          continue;
        }
        history.push({ depression, timestampMs: Number(hooks.timeAtSunDepression(depression)), supported: true, status: sample.status, reason: sample.reason ?? null, photopic: Number(sample.sky.channels.photopic.value) });
      }
      const firstUnsupported = history.find(x => !x.supported) ?? null;
      const levelBHistory = history.filter(x => x.supported).map(x => ({
        timestampMs: x.timestampMs,
        adaptationFieldLuminanceCdM2: x.photopic,
        detectionBackgroundLuminanceCdM2: x.photopic,
        photopicLuminanceCdM2: x.photopic,
        sunDepressionDeg: x.depression,
      }));
      const brightenings = [];
      for (let i = 1; i < levelBHistory.length; i += 1) {
        const previous = levelBHistory[i - 1];
        const current = levelBHistory[i];
        if (current.adaptationFieldLuminanceCdM2 > previous.adaptationFieldLuminanceCdM2 * (1 + 1e-9)) {
          const absolute = current.adaptationFieldLuminanceCdM2 - previous.adaptationFieldLuminanceCdM2;
          const fractional = absolute / previous.adaptationFieldLuminanceCdM2;
          brightenings.push({
            fromSunDepressionDeg: previous.sunDepressionDeg,
            toSunDepressionDeg: current.sunDepressionDeg,
            fromPhotopicCdM2: previous.adaptationFieldLuminanceCdM2,
            toPhotopicCdM2: current.adaptationFieldLuminanceCdM2,
            absoluteIncreaseCdM2: absolute,
            fractionalIncrease: fractional,
            percentIncrease: fractional * 100,
          });
        }
      }
      let directBuild = { status: 'READY', detail: null };
      try {
        prehistory.buildContinuousSunsetAdaptationTimeline({
          levelBHistory,
          sunsetMs: spec.sunsetMs,
          timeAtSunDepression: hooks.timeAtSunDepression,
          tauSeconds: transient.DEFAULT_TRANSIENT_ADAPTATION_TAU_SECONDS,
        });
      } catch (error) {
        directBuild = { status: 'REJECTED', detail: String(error?.message ?? error), code: error?.code ?? null };
      }
      const maximumBrightening = brightenings.length
        ? brightenings.reduce((a, b) => b.fractionalIncrease > a.fractionalIncrease ? b : a)
        : null;
      return {
        key,
        name: entry.row?.name ?? null,
        transientResult: {
          status: entry.result?.status ?? null,
          reason: entry.result?.reason ?? null,
          detail: entry.result?.detail ?? null,
          supportAudit: entry.result?.transientSupportAudit ?? null,
        },
        sampledHistoryCount: history.length,
        firstUnsupported,
        firstPhotopicCdM2: levelBHistory[0]?.adaptationFieldLuminanceCdM2 ?? null,
        lastPhotopicCdM2: levelBHistory.at(-1)?.adaptationFieldLuminanceCdM2 ?? null,
        brighteningTransitionCount: brightenings.length,
        firstBrightening: brightenings[0] ?? null,
        maximumBrightening,
        totalNetRatioLastToFirst: levelBHistory.length ? levelBHistory.at(-1).adaptationFieldLuminanceCdM2 / levelBHistory[0].adaptationFieldLuminanceCdM2 : null,
        directPrehistoryBuild: directBuild,
      };
    });
    return { atmosphereResolution: evaluation.atmosphereResolution, results };
  }, spec);

  const outDir = path.join(process.env.RUNNER_TEMP, 'transient-prehistory-detail');
  fs.mkdirSync(outDir, { recursive: true });
  const payload = {
    schemaVersion: 1,
    status: 'TRANSIENT_PREHISTORY_BRIGHTENING_DIAGNOSTIC_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    spec,
    audit,
    claimBoundary: { diagnosticOnly: true, transientExperimental: true, noModelChange: true, noTuning: true, F314Unchanged: true, tauUnchanged: true, noMYSTIC: true },
    browserConsole,
  };
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(payload, null, 2) + '\n');
  console.log('TRANSIENT_PREHISTORY_DETAIL=' + JSON.stringify({ label, results: audit.results }));
} finally {
  await browser.close();
}

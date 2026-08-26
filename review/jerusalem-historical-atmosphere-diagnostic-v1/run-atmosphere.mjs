import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const env = process.env;
const spec = Object.freeze({
  label: env.CASE_LABEL,
  civilDate: env.CASE_DATE,
  hebrewLabel: env.HEBREW_LABEL,
  latitudeDeg: Number(env.LATITUDE_DEG),
  longitudeDeg: Number(env.LONGITUDE_DEG),
  observerElevationM: Number(env.OBSERVER_ELEVATION_M),
  timeZone: env.TIME_ZONE,
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const consoleLines = [];
  page.on('console', m => consoleLines.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => consoleLines.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  const diagnostic = await page.evaluate(async spec => {
    const sunsetMs = Number(eval('sunsetAtSeaLevel')(spec.civilDate, spec.timeZone, spec.latitudeDeg, spec.longitudeDeg));
    if (!Number.isFinite(sunsetMs)) throw new Error('sunset unavailable');
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, sunsetMs);
    const referenceTimeMs = Number(hooks.timeAtSunDepression(6.0));
    if (!Number.isFinite(referenceTimeMs)) throw new Error('6-degree reference time unavailable');
    const resolver = await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const resolution = await resolver.resolvePreviewLevelBAtmosphere({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      validTimeMs: referenceTimeMs,
      fetchImpl: globalThis.fetch,
      now: new Date(),
    });
    return {
      sunsetMs,
      sunsetIso: new Date(sunsetMs).toISOString(),
      referenceTimeMs,
      referenceTimeIso: new Date(referenceTimeMs).toISOString(),
      browserNowIso: new Date().toISOString(),
      resolution,
    };
  }, spec);
  const output = {
    schemaVersion: 1,
    status: 'JERUSALEM_HISTORICAL_ATMOSPHERE_DIAGNOSTIC',
    applicationSha: env.APPLICATION_SHA,
    preregisteredCase: spec,
    diagnostic,
    claimBoundary: {
      atmosphereDiagnosticOnly: true,
      noVisibilityResult: true,
      noTuning: true,
      noProviderSubstitution: true,
      pandoraOpened: false,
    },
    browserConsole: consoleLines,
  };
  const outDir = path.join(env.RUNNER_TEMP, 'jerusalem-historical-atmosphere');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, `${spec.label}.json`), JSON.stringify(output, null, 2) + '\n');
  console.log('ATMOSPHERE_DIAGNOSTIC_SUMMARY=' + JSON.stringify({
    label: spec.label,
    referenceTimeIso: diagnostic.referenceTimeIso,
    status: diagnostic.resolution?.status ?? null,
    selectedProviderId: diagnostic.resolution?.selectedProviderId ?? null,
    aod550: diagnostic.resolution?.atmosphere?.aod550 ?? null,
    attempts: diagnostic.resolution?.attempts ?? [],
  }));
} finally {
  await browser.close();
}

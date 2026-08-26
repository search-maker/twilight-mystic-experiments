import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  'tishrei-transient-overlap': {
    civilDate: '2025-09-23',
    sunsetMs: 1758641660932,
  },
  'tammuz-transient-overlap': {
    civilDate: '2026-06-16',
    sunsetMs: 1781628380546,
  },
};

const label = process.env.CASE_LABEL;
const frozen = CASES[label];
if (!frozen) throw new Error(`unknown CASE_LABEL ${label}`);
const spec = Object.freeze({
  label,
  civilDate: frozen.civilDate,
  sunsetMs: frozen.sunsetMs,
  latitudeDeg: 31.778,
  longitudeDeg: 35.235,
  observerElevationM: 800,
  timeZone: 'Asia/Jerusalem',
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(spec => {
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, spec.sunsetMs);
    const altitudeAtSunsetDeg = Number(sunAltitude(spec.sunsetMs, spec.latitudeDeg, spec.longitudeDeg));
    const actualDepressionAtSunsetDeg = -altitudeAtSunsetDeg;
    const depths = [0, 0.1, 0.5, 0.833, 1.0, 2.0];
    const roots = Object.fromEntries(depths.map(depth => {
      const raw = hooks.timeAtSunDepression(depth);
      const timestampMs = Number.isFinite(raw) ? Number(raw) : null;
      return [String(depth), {
        depthDeg: depth,
        timestampMs,
        minutesFromApplicationSunset: timestampMs == null ? null : (timestampMs - spec.sunsetMs) / 60000,
        sunAltitudeAtRootDeg: timestampMs == null ? null : Number(sunAltitude(timestampMs, spec.latitudeDeg, spec.longitudeDeg)),
      }];
    }));
    return {
      altitudeAtApplicationSunsetDeg: altitudeAtSunsetDeg,
      actualDepressionAtApplicationSunsetDeg: actualDepressionAtSunsetDeg,
      roots,
    };
  }, spec);

  const outDir = path.join(process.env.RUNNER_TEMP, 'sunset-depth-audit');
  fs.mkdirSync(outDir, { recursive: true });
  const payload = {
    schemaVersion: 1,
    status: 'APPLICATION_SUNSET_VS_GEOMETRIC_DEPTH_AUDIT_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    spec,
    audit,
    claimBoundary: {
      diagnosticOnly: true,
      noApplicationChange: true,
      noModelChange: true,
      noTuning: true,
      F314Unchanged: true,
      tauUnchanged: true,
      noMYSTIC: true,
    },
    browserConsole,
  };
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify(payload, null, 2) + '\n');
  console.log('SUNSET_DEPTH_AUDIT=' + JSON.stringify({ label, ...audit }));
} finally {
  await browser.close();
}

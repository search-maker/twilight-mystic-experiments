import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });
  const result = await page.evaluate(async () => {
    const spec = { latitudeDeg:31.778, longitudeDeg:35.235, observerElevationM:800, date:'2025-09-23', timeZone:'Asia/Jerusalem', sunsetMs:1758641660932, expectedAod550:0.22 };
    const set=(id,v)=>{const e=document.getElementById(id); if(!e) throw new Error(`missing ${id}`); e.value=String(v); e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));};
    localStorage.clear();
    set('calculatorFeature','three-star'); set('lat',spec.latitudeDeg); set('lon',spec.longitudeDeg); set('date',spec.date); set('timezone',spec.timeZone); set('observerElevationM',spec.observerElevationM); set('visibilityEngineMode','level-b-v3-crumey-blackwell-equilibrium'); set('threeStarCount',3); set('threeStarMagnitudeBasis','effective'); set('threeStarMagnitudeThreshold',1.7);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__='level-b-v3-crumey-blackwell-equilibrium'; globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function') await eval('ensureBuiltInCatalogReady()');
    const hooks=eval('__levelBSitewideGeometryHooks')({latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,date:spec.date,timeZone:spec.timeZone},spec.sunsetMs);
    const adapter=await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver=await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const transient=await import('/scientific-tools/visibility-v3/level-b-transient-contiguous-support.mjs');
    const runtimeData=await adapter.loadValidatedV3RuntimeData({fetchImpl:globalThis.fetch});
    const atmosphereResolution=await resolver.resolvePreviewLevelBAtmosphere({latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,validTimeMs:hooks.timeAtSunDepression(6),fetchImpl:globalThis.fetch});
    if(atmosphereResolution.status!=='RESOLVED'||Math.abs(Number(atmosphereResolution.atmosphere.aod550)-spec.expectedAod550)>1e-12) throw new Error('atmosphere drift');
    delete globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const rows=globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    if(!Array.isArray(rows)||rows.length!==7653) throw new Error(`rows ${rows?.length}`);
    const row=rows.find(r=>Number(r.hr)===4295);
    if(!row) throw new Error('Merak HR4295 missing');
    const target=engine.normalizeSitewideTarget(row);
    const sunsetDep=-Number(eval('sunAltitude')(spec.sunsetMs,spec.latitudeDeg,spec.longitudeDeg));
    const outputs=[];
    for(const tauSeconds of [20,30,45,60]){
      const r=await transient.evaluateLevelBTransientWithContiguousSupport({runtimeData,target,observerElevationM:spec.observerElevationM,sunsetMs:spec.sunsetMs,sunDepressionAtSunsetDeg:sunsetDep,geometryAtSunDepression:hooks.geometryAtSunDepression,timeAtSunDepression:hooks.timeAtSunDepression,atmosphereResolution,scanStepDeg:0.10,transientTauSeconds:tauSeconds});
      outputs.push({tauSeconds,result:r});
    }
    return {row,target,sunsetDep,atmosphereResolution,outputs};
  });
  const out=path.join(process.env.RUNNER_TEMP,'transient-monotonicity-audit'); fs.mkdirSync(out,{recursive:true}); fs.writeFileSync(path.join(out,'merak.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result.outputs.map(x=>({tau:x.tauSeconds,status:x.result.status,reason:x.result.reason,minutes:x.result.minutesAfterSunset,depression:x.result.sunDepressionDeg,margin:x.result.visibilityMarginMag,penalty:x.result.transientAdaptationPenaltyMag,intervals:x.result.timeline?.visibilityIntervals})),null,2));
} finally { await browser.close(); }

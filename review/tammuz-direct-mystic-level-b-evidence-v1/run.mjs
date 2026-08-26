import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const frozen=Object.freeze({
  civilDate:'2026-06-16',
  latitudeDeg:31.778,
  longitudeDeg:35.235,
  observerElevationM:800,
  timeZone:'Asia/Jerusalem',
  engineMode:'level-b-v3-crumey-blackwell-equilibrium',
  threshold:1.7,
  requiredCount:3,
  stabilityMs:60000,
  sunsetMs:1781628380546,
  eventTimeMs:1781629701483.5,
  expectedAod550:0.18,
  expectedKeys:['HR 5191','HR 4905','HR 3982'],
});

const browser=await chromium.launch({headless:true});
try{
  const page=await browser.newPage();
  const browserConsole=[];
  page.on('console',m=>browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror',e=>browserConsole.push(`[pageerror] ${e.stack||e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/',{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForSelector('#visibilityEngineMode',{timeout:120000});

  const audit=await page.evaluate(async frozen=>{
    const set=(id,v)=>{const e=document.getElementById(id);if(!e)throw new Error(`missing #${id}`);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){}
    set('calculatorFeature','three-star');
    set('lat',frozen.latitudeDeg);set('lon',frozen.longitudeDeg);set('date',frozen.civilDate);set('timezone',frozen.timeZone);set('observerElevationM',frozen.observerElevationM);
    set('visibilityEngineMode',frozen.engineMode);set('threeStarCount',frozen.requiredCount);set('threeStarMagnitudeBasis','effective');set('threeStarMagnitudeThreshold',frozen.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__=frozen.engineMode;globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function')await eval('ensureBuiltInCatalogReady()');
    const rawCount=Array.isArray(globalThis.__STARS_BUILT_IN_STARS__)?globalThis.__STARS_BUILT_IN_STARS__.length:-1;
    if(rawCount!==9090)throw new Error(`raw catalog ${rawCount}`);

    const input={latitudeDeg:frozen.latitudeDeg,longitudeDeg:frozen.longitudeDeg,observerElevationM:frozen.observerElevationM,date:frozen.civilDate,timeZone:frozen.timeZone};
    const hooks=eval('__levelBSitewideGeometryHooks')(input,Number(frozen.sunsetMs));
    const adapter=await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver=await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const runtimeData=await adapter.loadValidatedV3RuntimeData({fetchImpl:globalThis.fetch});
    const referenceTimeMs=hooks.timeAtSunDepression(6.0);
    const atmosphereResolution=await resolver.resolvePreviewLevelBAtmosphere({latitudeDeg:frozen.latitudeDeg,longitudeDeg:frozen.longitudeDeg,observerElevationM:frozen.observerElevationM,validTimeMs:referenceTimeMs,fetchImpl:globalThis.fetch});
    if(atmosphereResolution.status!=='RESOLVED')throw new Error(`atmosphere ${atmosphereResolution.status}`);
    if(Math.abs(Number(atmosphereResolution.atmosphere?.aod550)-frozen.expectedAod550)>1e-12)throw new Error(`AOD drift ${atmosphereResolution.atmosphere?.aod550}`);

    delete globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui=JSON.parse(JSON.stringify(eval('threeStarResultData')));
    const snapshot=globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    if(!Array.isArray(snapshot)||snapshot.length!==7653)throw new Error(`transformed snapshot ${snapshot?.length}`);
    if(globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__!==undefined)throw new Error('temporary direct handoff not cleaned');
    const uiEventMs=Number(ui?.eventTime??ui?.eventTimeMs??ui?.time);
    if(!Number.isFinite(uiEventMs)||Math.abs(uiEventMs-frozen.eventTimeMs)>500)throw new Error(`UI event drift ${uiEventMs}`);
    const uiKeys=(ui?.stars??[]).map(s=>s.key??s.catalogId);
    if(JSON.stringify(uiKeys)!==JSON.stringify(frozen.expectedKeys))throw new Error(`UI determining keys drift ${JSON.stringify(uiKeys)}`);

    const catalogId=row=>row?.isPlanet?(row.planetKey?`PLANET:${row.planetKey}`:`PLANET:${row.name}`):row?.hip!=null&&row.hip!==''?`HIP ${row.hip}`:row?.hr!=null&&row.hr!==''?`HR ${row.hr}`:row?.hd!=null&&row.hd!==''?`HD ${row.hd}`:(row?.name??row?.id??'target');
    const rows=snapshot.map(r=>({...r}));
    const entries=rows.map(row=>({key:catalogId(row),row,target:engine.normalizeSitewideTarget(row)})).filter(e=>e.target);
    const byKey=new Map(entries.map(e=>[e.key,e]));
    const point=engine.createSitewidePointEvaluator({runtimeData,atmosphereResolution,geometryAtSunDepression:hooks.geometryAtSunDepression});
    const depressionAt=t=>-Number(eval('sunAltitude')(Number(t),frozen.latitudeDeg,frozen.longitudeDeg));

    const evidence=frozen.expectedKeys.map(key=>{
      const entry=byKey.get(key);if(!entry)throw new Error(`missing transformed entry ${key}`);
      const samples=[0,30000,60000].map(offsetMs=>{
        const timeMs=frozen.eventTimeMs+offsetMs;
        const sunDepressionDeg=depressionAt(timeMs);
        const geometry=hooks.geometryAtSunDepression(sunDepressionDeg,entry.target);
        const sample=point(entry.target,sunDepressionDeg);
        if(sample?.status!=='SUPPORTED')throw new Error(`${key} unsupported at +${offsetMs}ms: ${sample?.status}`);
        return{offsetMs,timeMs,sunDepressionDeg,geometry,sample};
      });
      return{key,name:entry.row?.name??null,transformedRow:entry.row,normalizedTarget:entry.target,samples};
    });

    const eventSamples=evidence.map(e=>e.samples[0].sample);
    for(let i=0;i<eventSamples.length;i+=1){
      const margin=Number(eventSamples[i]?.visibility?.visibilityMarginMag);
      if(!Number.isFinite(margin)||margin<-1e-8)throw new Error(`${evidence[i].key} event margin ${margin}`);
    }

    return{
      frozen,
      rawCatalogCount:rawCount,
      transformedCatalogCount:rows.length,
      ui,
      referenceTimeMs,
      atmosphereResolution,
      eventSunDepressionDeg:depressionAt(frozen.eventTimeMs),
      evidence,
    };
  },frozen);

  const outDir=path.join(process.env.RUNNER_TEMP,'tammuz-direct-mystic-level-b-evidence');
  fs.mkdirSync(outDir,{recursive:true});
  const payload={schemaVersion:1,status:'TAMMUZ_DIRECT_MYSTIC_LEVEL_B_EVIDENCE_FROZEN',applicationSha:process.env.APPLICATION_SHA,audit,browserConsole,claimBoundary:{transformedRowsOnly:true,F314Unchanged:true,noTuning:true,noMYSTIC:true,noProduction:true,noPandora:true}};
  fs.writeFileSync(path.join(outDir,'level-b-event-evidence.json'),JSON.stringify(payload,null,2)+'\n');
  console.log('TAMMUZ_LEVEL_B_EVIDENCE='+JSON.stringify({eventTimeMs:audit.frozen.eventTimeMs,eventSunDepressionDeg:audit.eventSunDepressionDeg,aod550:audit.atmosphereResolution.atmosphere.aod550,keys:audit.evidence.map(e=>e.key),eventMargins:audit.evidence.map(e=>e.samples[0].sample.visibility.visibilityMarginMag)}));
}finally{await browser.close();}

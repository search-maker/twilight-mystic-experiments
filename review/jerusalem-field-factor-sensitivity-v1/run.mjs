// Trigger-only comment; frozen sensitivity logic and inputs unchanged.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES={
  tishrei:{date:'2025-09-23',sunsetMs:1758641660932,expectedAod550:0.22,baselineEventMs:1758642904994.5},
  nisan:{date:'2026-03-19',sunsetMs:1773935382953.0005,expectedAod550:0.43,baselineEventMs:null},
  tammuz:{date:'2026-06-16',sunsetMs:1781628380546,expectedAod550:0.18,baselineEventMs:1781629701483.5},
};
const caseId=process.env.CASE_ID;
const frozen=CASES[caseId];
if(!frozen)throw new Error(`unknown CASE_ID ${caseId}`);
const fieldFactors=[3.14,2.4,2.0];

const browser=await chromium.launch({headless:true});
try{
  const page=await browser.newPage();
  const browserConsole=[];
  page.on('console',m=>browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror',e=>browserConsole.push(`[pageerror] ${e.stack||e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/',{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForSelector('#visibilityEngineMode',{timeout:120000});
  const audit=await page.evaluate(async({caseId,frozen,fieldFactors})=>{
    const spec={latitudeDeg:31.778,longitudeDeg:35.235,observerElevationM:800,date:frozen.date,timeZone:'Asia/Jerusalem',engineMode:'level-b-v3-crumey-blackwell-equilibrium',threshold:1.7,requiredCount:3,stabilityMs:60000,scanStepMs:30000,baselineF:3.14};
    const set=(id,v)=>{const e=document.getElementById(id);if(!e)throw new Error(`missing #${id}`);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){}
    set('calculatorFeature','three-star');set('lat',spec.latitudeDeg);set('lon',spec.longitudeDeg);set('date',spec.date);set('timezone',spec.timeZone);set('observerElevationM',spec.observerElevationM);set('visibilityEngineMode',spec.engineMode);set('threeStarCount',spec.requiredCount);set('threeStarMagnitudeBasis','effective');set('threeStarMagnitudeThreshold',spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__=spec.engineMode;globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function')await eval('ensureBuiltInCatalogReady()');
    const rawCount=Array.isArray(globalThis.__STARS_BUILT_IN_STARS__)?globalThis.__STARS_BUILT_IN_STARS__.length:-1;
    if(rawCount!==9090)throw new Error(`raw catalog ${rawCount}`);

    let rows;
    globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__=true;
    try{
      await eval('calculate()');
      const handoff=globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__;
      if(!Array.isArray(handoff)||handoff.length<1000)throw new Error(`handoff ${handoff?.length}`);
      rows=handoff.map(r=>({...r}));
    }finally{
      delete globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__;
      delete globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__;
    }

    const input={latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,date:spec.date,timeZone:spec.timeZone};
    const hooks=eval('__levelBSitewideGeometryHooks')(input,Number(frozen.sunsetMs));
    const sunsetResidual=Number(eval('sunAltitude')(Number(frozen.sunsetMs),spec.latitudeDeg,spec.longitudeDeg));
    const adapter=await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver=await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const runtimeData=await adapter.loadValidatedV3RuntimeData({fetchImpl:globalThis.fetch});
    const referenceTimeMs=hooks.timeAtSunDepression(6.0);
    const atmosphereResolution=await resolver.resolvePreviewLevelBAtmosphere({latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,validTimeMs:referenceTimeMs,fetchImpl:globalThis.fetch});
    if(atmosphereResolution.status!=='RESOLVED')throw new Error(`atmosphere ${atmosphereResolution.status}`);
    if(Math.abs(Number(atmosphereResolution.atmosphere?.aod550)-Number(frozen.expectedAod550))>1e-12)throw new Error(`AOD changed: ${atmosphereResolution.atmosphere?.aod550} expected ${frozen.expectedAod550}`);
    const point=engine.createSitewidePointEvaluator({runtimeData,atmosphereResolution,geometryAtSunDepression:hooks.geometryAtSunDepression});
    const catalogId=row=>row?.isPlanet?(row.planetKey?`PLANET:${row.planetKey}`:`PLANET:${row.name}`):row?.hip!=null&&row.hip!==''?`HIP ${row.hip}`:row?.hr!=null&&row.hr!==''?`HR ${row.hr}`:row?.hd!=null&&row.hd!==''?`HD ${row.hd}`:(row?.name??row?.id??'target');
    const candidates=rows.map(row=>({key:catalogId(row),row,target:engine.normalizeSitewideTarget(row)})).filter(e=>e.target);
    const depressionAt=t=>-Number(eval('sunAltitude')(t,spec.latitudeDeg,spec.longitudeDeg));
    const endMs=hooks.timeAtSunDepression(10.5);
    if(!Number.isFinite(endMs))throw new Error('10.5-degree end unavailable');
    const cache=new Map();
    const sampleAt=(entry,t)=>{
      const key=`${entry.key}|${Math.round(Number(t)/250)}`;
      if(!cache.has(key)){
        const d=depressionAt(t);
        cache.set(key,d>=2&&d<=10.5?point(entry.target,d):null);
      }
      return cache.get(key);
    };
    const results=[];
    for(const F of fieldFactors){
      const marginShiftMag=2.5*Math.log10(spec.baselineF/F);
      const qualifiesAt=(entry,t)=>{
        const d=depressionAt(t);
        if(!Number.isFinite(d)||d<2||d>10.5)return false;
        const s=sampleAt(entry,t);
        const baseMargin=Number(s?.visibility?.visibilityMarginMag);
        const apparent=Number(s?.stellar?.apparentVMagAtEye);
        return s?.status==='SUPPORTED'&&Number.isFinite(baseMargin)&&baseMargin+marginShiftMag>=-1e-10&&Number.isFinite(apparent)&&apparent>=spec.threshold-1e-10;
      };
      const event=engine.findStableSimultaneousQualifiedEvent(candidates,{requiredCount:spec.requiredCount,stabilityMs:spec.stabilityMs,startMs:Number(frozen.sunsetMs),endMs,scanStepMs:spec.scanStepMs,qualifiesAt});
      const selected=event.found?event.selected.map(entry=>{
        const s=sampleAt(entry,event.eventTimeMs);
        const baseMargin=Number(s?.visibility?.visibilityMarginMag);
        const apparent=Number(s?.stellar?.apparentVMagAtEye);
        return{key:entry.key,name:entry.row?.name,catalogMagnitude:Number(entry.row?.mag),apparentVMagAtEye:apparent,baseF314MarginMag:baseMargin,sensitivityMarginMag:baseMargin+marginShiftMag,limitingVMagnitudeF314:Number(s?.visibility?.limitingVMagnitude),limitingVMagnitudeSensitivity:Number(s?.visibility?.limitingVMagnitude)+marginShiftMag,geometry:hooks.geometryAtSunDepression(depressionAt(event.eventTimeMs),entry.target),completing:event.completingKeys?.includes(entry.key)??false};
      }):[];
      results.push({fieldFactor:F,marginShiftMag,found:event.found,eventTimeMs:event.found?event.eventTimeMs:null,minutesAfterSunset:event.found?(event.eventTimeMs-Number(frozen.sunsetMs))/60000:null,sunDepressionDeg:event.found?depressionAt(event.eventTimeMs):null,selected,completingKeys:event.completingKeys??[]});
    }
    const baseline=results.find(r=>r.fieldFactor===3.14);
    if(frozen.baselineEventMs==null){if(baseline.found)throw new Error(`baseline unexpectedly found event ${baseline.eventTimeMs}`);}else{if(!baseline.found)throw new Error('baseline expected event missing');if(Math.abs(baseline.eventTimeMs-Number(frozen.baselineEventMs))>500)throw new Error(`baseline event mismatch ${baseline.eventTimeMs} vs ${frozen.baselineEventMs}`);}
    return{caseId,spec,frozen,rawCatalogCount:rawCount,directCatalogRowCount:rows.length,sunsetResidualDeg:sunsetResidual,atmosphereResolution,referenceTimeMs,results,baseSampleCacheSize:cache.size};
  },{caseId,frozen,fieldFactors});
  const out=path.join(process.env.RUNNER_TEMP,'jerusalem-field-factor-sensitivity');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,`${caseId}.json`),JSON.stringify({schemaVersion:1,status:'JERUSALEM_FIELD_FACTOR_SENSITIVITY_COMPLETE',applicationSha:process.env.APPLICATION_SHA,audit,browserConsole,claimBoundary:{sensitivityOnly:true,productionDefaultChanged:false,baselineF314Unchanged:true,noTuning:true,noMYSTIC:true,noPandora:true}},null,2)+'\n');
  console.log('F_SENSITIVITY='+JSON.stringify({caseId,atmosphere:audit.atmosphereResolution,results:audit.results}));
}finally{await browser.close();}

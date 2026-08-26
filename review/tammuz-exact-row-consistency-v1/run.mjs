import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser=await chromium.launch({headless:true});
try{
  const page=await browser.newPage();
  const browserConsole=[];
  page.on('console',m=>browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror',e=>browserConsole.push(`[pageerror] ${e.stack||e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/',{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForSelector('#visibilityEngineMode',{timeout:120000});
  const audit=await page.evaluate(async()=>{
    const spec={latitudeDeg:31.778,longitudeDeg:35.235,observerElevationM:800,date:'2026-06-16',timeZone:'Asia/Jerusalem',engineMode:'level-b-v3-crumey-blackwell-equilibrium',threshold:1.7};
    const set=(id,v)=>{const e=document.getElementById(id);if(!e)throw new Error(`missing #${id}`);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){}
    set('calculatorFeature','three-star');set('lat',spec.latitudeDeg);set('lon',spec.longitudeDeg);set('date',spec.date);set('timezone',spec.timeZone);set('observerElevationM',spec.observerElevationM);set('visibilityEngineMode',spec.engineMode);set('threeStarCount',3);set('threeStarMagnitudeBasis','effective');set('threeStarMagnitudeThreshold',spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__=spec.engineMode;globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function')await eval('ensureBuiltInCatalogReady()');
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui=JSON.parse(JSON.stringify(eval('threeStarResultData')));
    if(!ui?.found||!Array.isArray(ui.stars)||ui.stars.length!==3)throw new Error(`unexpected UI event ${JSON.stringify({found:ui?.found,reason:ui?.reason,stars:ui?.stars?.length})}`);

    let exactRows;
    globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__=true;
    try{
      await eval('calculate()');
      const handoff=globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__;
      if(!Array.isArray(handoff)||handoff.length<1000)throw new Error(`handoff ${handoff?.length}`);
      exactRows=handoff.map(r=>({...r}));
    }finally{
      delete globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__;
      delete globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__;
    }

    const catalogId=row=>row?.isPlanet?(row.planetKey?`PLANET:${row.planetKey}`:`PLANET:${row.name}`):row?.hip!=null&&row.hip!==''?`HIP ${row.hip}`:row?.hr!=null&&row.hr!==''?`HR ${row.hr}`:row?.hd!=null&&row.hd!==''?`HD ${row.hd}`:(row?.name??row?.id??'target');
    const selectedRows=ui.stars.map(star=>{
      const row=exactRows.find(r=>catalogId(r)===star.catalogId);
      if(!row)throw new Error(`missing transformed row ${star.catalogId}`);
      return row;
    });
    const sunsetMs=Number(ui.sunsetTime),eventTimeMs=Number(ui.eventTime);
    const input={latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,date:spec.date,timeZone:spec.timeZone};
    const hooks=eval('__levelBSitewideGeometryHooks')(input,sunsetMs);
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const evaluation=await engine.evaluateSitewideRows({rows:selectedRows,latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,sunsetMs,geometryAtSunDepression:hooks.geometryAtSunDepression,timeAtSunDepression:hooks.timeAtSunDepression,engineMode:spec.engineMode,fetchImpl:globalThis.fetch});
    if(evaluation.status!=='COMPLETE')throw new Error(`evaluation ${evaluation.status}`);
    const point=engine.createSitewidePointEvaluator({runtimeData:evaluation.runtimeData,atmosphereResolution:evaluation.atmosphereResolution,geometryAtSunDepression:hooks.geometryAtSunDepression});
    const depressionAt=t=>-Number(eval('sunAltitude')(t,spec.latitudeDeg,spec.longitudeDeg));
    const byId=new Map(evaluation.results.map(e=>[catalogId(e.row),e]));
    const at=(entry,t)=>{const d=depressionAt(t);const sample=point(entry.target,d);const margin=Number(sample?.visibility?.visibilityMarginMag);const apparent=Number(sample?.stellar?.apparentVMagAtEye);return{timestampMs:t,sunDepressionDeg:d,status:sample?.status,visibilityMarginMag:margin,apparentVMagAtEye:apparent,limitingVMagnitude:Number(sample?.visibility?.limitingVMagnitude),qualifies:sample?.status==='SUPPORTED'&&margin>=-1e-10&&apparent>=spec.threshold-1e-10,geometry:hooks.geometryAtSunDepression(d,entry.target)};};
    const stars=ui.stars.map(star=>{const entry=byId.get(star.catalogId);if(!entry)throw new Error(`missing evaluation ${star.catalogId}`);return{name:star.name,catalogId:star.catalogId,uiFirstVisibleTime:star.firstVisibleTime,uiCompleting:star.completing,timelineIntervalsMs:entry.intervalsMs,event:at(entry,eventTimeMs),plus30:at(entry,eventTimeMs+30000),plus60:at(entry,eventTimeMs+60000),transformedRow:{raHours:entry.target.raHours,decDeg:entry.target.decDeg,mag:Number(entry.row?.mag),epoch:entry.row?.epoch??null}};});
    return{spec,ui,directCatalogRowCount:exactRows.length,atmosphereResolution:evaluation.atmosphereResolution,stars};
  });
  for(const s of audit.stars){if(!s.event.qualifies||!s.plus30.qualifies||!s.plus60.qualifies)throw new Error(`Selected star fails independent exact-row consistency: ${JSON.stringify(s)}`);}
  const out=path.join(process.env.RUNNER_TEMP,'tammuz-exact-row-consistency');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({schemaVersion:1,status:'TAMMUZ_EXACT_TRANSFORMED_ROW_CONSISTENCY_PASS',applicationSha:process.env.APPLICATION_SHA,audit,browserConsole,claimBoundary:{diagnosticOnly:true,noTuning:true,F314Unchanged:true,noMYSTIC:true,noPandora:true}},null,2)+'\n');
  console.log('TAMMUZ_EXACT_ROW='+JSON.stringify({ui:{eventTime:audit.ui.eventTime,minutesAfterSunset:audit.ui.minutesAfterSunset,sunAltitude:audit.ui.sunAltitude},atmosphere:audit.atmosphereResolution,stars:audit.stars}));
}finally{await browser.close();}

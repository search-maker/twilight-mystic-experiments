import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });
  const audit = await page.evaluate(async () => {
    const spec={latitudeDeg:31.778,longitudeDeg:35.235,observerElevationM:800,date:'2026-03-19',timeZone:'Asia/Jerusalem',engineMode:'level-b-v3-crumey-blackwell-equilibrium',threshold:1.7};
    const set=(id,v)=>{const e=document.getElementById(id);if(!e)throw new Error(`missing #${id}`);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){ }
    set('calculatorFeature','three-star'); set('lat',spec.latitudeDeg); set('lon',spec.longitudeDeg); set('date',spec.date); set('timezone',spec.timeZone); set('observerElevationM',spec.observerElevationM); set('visibilityEngineMode',spec.engineMode); set('threeStarCount',3); set('threeStarMagnitudeBasis','effective'); set('threeStarMagnitudeThreshold',spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__=spec.engineMode; globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function') await eval('ensureBuiltInCatalogReady()');
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui=JSON.parse(JSON.stringify(eval('threeStarResultData')));
    const catalogAll=globalThis.__STARS_BUILT_IN_STARS__; const canRise=eval('canGeometricallyRise'); const rows=catalogAll.filter(s=>canRise(s,spec.latitudeDeg)).map(s=>({...s}));
    const sunsetMs=Number(ui.sunsetTime); const input={latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,date:spec.date,timeZone:spec.timeZone}; const hooks=eval('__levelBSitewideGeometryHooks')(input,sunsetMs);
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const evaluation=await engine.evaluateSitewideRows({rows,latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,sunsetMs,geometryAtSunDepression:hooks.geometryAtSunDepression,timeAtSunDepression:hooks.timeAtSunDepression,engineMode:spec.engineMode,fetchImpl:globalThis.fetch});
    if(evaluation.status!=='COMPLETE') throw new Error(`evaluation ${evaluation.status}`);
    const point=engine.createSitewidePointEvaluator({runtimeData:evaluation.runtimeData,atmosphereResolution:evaluation.atmosphereResolution,geometryAtSunDepression:hooks.geometryAtSunDepression});
    const entries=evaluation.results.filter(e=>e.target).map(e=>({row:e.row,target:e.target}));
    const id=r=>r?.hip!=null&&r.hip!==''?`HIP ${r.hip}`:r?.hr!=null&&r.hr!==''?`HR ${r.hr}`:r?.hd!=null&&r.hd!==''?`HD ${r.hd}`:(r?.name??r?.id??'target');
    const depths=[4,5,6,7,8,9,10,10.4];
    const profiles=depths.map(depression=>{
      const list=entries.map(entry=>{const s=point(entry.target,depression); const margin=Number(s?.visibility?.visibilityMarginMag); const apparent=Number(s?.stellar?.apparentVMagAtEye); const supported=s?.status==='SUPPORTED'; const visible=supported&&Number.isFinite(margin)&&margin>=-1e-10; const effective=supported&&Number.isFinite(apparent)&&apparent>=spec.threshold-1e-10; return {entry,s,supported,visible,effective,qualifies:visible&&effective,margin,apparent};});
      const statusCounts={}; for(const r of list){const k=r.s?.status??'NULL';statusCounts[k]=(statusCounts[k]??0)+1;}
      const compact=r=>({name:r.entry.row?.name,catalogId:id(r.entry.row),catalogMagnitude:Number(r.entry.row?.mag),status:r.s?.status,reason:r.s?.reason??null,margin:r.margin,apparentV:r.apparent,limit:Number(r.s?.visibility?.limitingVMagnitude),alt:Number(r.s?.geometry?.targetAltitudeDeg),relAz:Number(r.s?.geometry?.relativeAzimuthDeg)});
      const topByMargin=list.filter(r=>r.supported&&Number.isFinite(r.margin)).sort((a,b)=>b.margin-a.margin).slice(0,10).map(compact);
      const topEffectiveByMargin=list.filter(r=>r.effective&&Number.isFinite(r.margin)).sort((a,b)=>b.margin-a.margin).slice(0,10).map(compact);
      return {sunDepressionDeg:depression,statusCounts,supportedCount:list.filter(r=>r.supported).length,visibleCount:list.filter(r=>r.visible).length,effectivePassCount:list.filter(r=>r.effective).length,qualifyingCount:list.filter(r=>r.qualifies).length,topByMargin,topEffectiveByMargin};
    });
    return {spec,ui,rowsCount:rows.length,atmosphereResolution:evaluation.atmosphereResolution,profiles};
  });
  const out=path.join(process.env.RUNNER_TEMP,'nisan-support-profile'); fs.mkdirSync(out,{recursive:true}); fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({schemaVersion:1,status:'NISAN_SUPPORT_PROFILE_COMPLETE',applicationSha:process.env.APPLICATION_SHA,audit,claimBoundary:{diagnosticOnly:true,noTuning:true,F314Unchanged:true}},null,2)+'\n');
  console.log('NISAN_PROFILE='+JSON.stringify(audit.profiles));
} finally { await browser.close(); }

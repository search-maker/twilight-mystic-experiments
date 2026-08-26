import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil:'domcontentloaded', timeout:120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout:120000 });

  const audit = await page.evaluate(async () => {
    const spec = Object.freeze({
      latitudeDeg:31.778, longitudeDeg:35.235, observerElevationM:800,
      date:'2026-06-16', timeZone:'Asia/Jerusalem',
      engineMode:'level-b-v3-crumey-blackwell-equilibrium', threshold:1.7,
      requiredCount:3, stabilityMs:60_000, scanStepMs:30_000,
    });
    const set=(id,v)=>{const e=document.getElementById(id);if(!e)throw new Error(`missing #${id}`);e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){ }
    set('calculatorFeature','three-star'); set('lat',spec.latitudeDeg); set('lon',spec.longitudeDeg); set('date',spec.date); set('timezone',spec.timeZone); set('observerElevationM',spec.observerElevationM); set('visibilityEngineMode',spec.engineMode); set('threeStarCount',spec.requiredCount); set('threeStarMagnitudeBasis','effective'); set('threeStarMagnitudeThreshold',spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__=spec.engineMode; globalThis.__SKY_MAP_REQUEST__=false;
    if(typeof eval('ensureBuiltInCatalogReady')==='function') await eval('ensureBuiltInCatalogReady()');
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const ui=JSON.parse(JSON.stringify(eval('threeStarResultData')));
    if(!ui?.found) throw new Error(`Tammuz UI event missing: ${ui?.reason}`);
    if(!ui.stars?.some(s=>s.catalogId==='HR 3982')) throw new Error('Regulus not in UI triple');

    const catalogAll=globalThis.__STARS_BUILT_IN_STARS__;
    const canRise=eval('canGeometricallyRise');
    const rows=catalogAll.filter(s=>canRise(s,spec.latitudeDeg)).map(s=>({...s}));
    const catalogId=row=>row?.hip!=null&&row.hip!==''?`HIP ${row.hip}`:row?.hr!=null&&row.hr!==''?`HR ${row.hr}`:row?.hd!=null&&row.hd!==''?`HD ${row.hd}`:(row?.name??row?.id??'target');
    const sunsetMs=Number(ui.sunsetTime);
    const input={latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,date:spec.date,timeZone:spec.timeZone};
    const hooks=eval('__levelBSitewideGeometryHooks')(input,sunsetMs);
    const sunAltitudeFn=eval('sunAltitude');
    const depressionAt=t=>-Number(sunAltitudeFn(t,spec.latitudeDeg,spec.longitudeDeg));
    const engine=await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const evaluation=await engine.evaluateSitewideRows({rows,latitudeDeg:spec.latitudeDeg,longitudeDeg:spec.longitudeDeg,observerElevationM:spec.observerElevationM,sunsetMs,geometryAtSunDepression:hooks.geometryAtSunDepression,timeAtSunDepression:hooks.timeAtSunDepression,engineMode:spec.engineMode,fetchImpl:globalThis.fetch});
    if(evaluation.status!=='COMPLETE') throw new Error(`evaluation ${evaluation.status}`);
    const point=engine.createSitewidePointEvaluator({runtimeData:evaluation.runtimeData,atmosphereResolution:evaluation.atmosphereResolution,geometryAtSunDepression:hooks.geometryAtSunDepression});
    const candidates=evaluation.results.filter(e=>e.target).map(e=>({key:catalogId(e.row),row:e.row,target:e.target,intervalsMs:e.intervalsMs,result:e.result}));
    const pointCache=new Map();
    const sampleAt=(entry,t)=>{
      const k=`${entry.key}|${Number(t).toFixed(3)}`;
      if(!pointCache.has(k)) pointCache.set(k,point(entry.target,depressionAt(t)));
      return pointCache.get(k);
    };
    const qualifiesAt=(entry,t)=>{
      const s=sampleAt(entry,t); const margin=Number(s?.visibility?.visibilityMarginMag); const apparent=Number(s?.stellar?.apparentVMagAtEye);
      return s?.status==='SUPPORTED' && Number.isFinite(margin) && margin>=-1e-10 && Number.isFinite(apparent) && apparent>=spec.threshold-1e-10;
    };
    const endMs=hooks.timeAtSunDepression(10.5) ?? (sunsetMs+8*3600e3);
    const directEvent=engine.findStableSimultaneousQualifiedEvent(candidates,{requiredCount:3,stabilityMs:spec.stabilityMs,startMs:sunsetMs,endMs,scanStepMs:spec.scanStepMs,qualifiesAt});
    if(!directEvent.found) throw new Error('direct pointwise event missing');
    const regulus=candidates.find(e=>e.key==='HR 3982');
    if(!regulus) throw new Error('Regulus row missing');

    const compactSample=(t)=>{const s=sampleAt(regulus,t);return {timestampMs:t,sunDepressionDeg:depressionAt(t),status:s?.status??null,margin:Number(s?.visibility?.visibilityMarginMag),apparentV:Number(s?.stellar?.apparentVMagAtEye),limitingV:Number(s?.visibility?.limitingVMagnitude),geometry:s?.geometry??null,support:s?.support??null};};
    const findFalseTrue=(predicate,lo0,hi0)=>{let lo=lo0,hi=hi0;if(predicate(lo))return lo;if(!predicate(hi))return null;for(let i=0;i<40&&hi-lo>0.05;i++){const mid=(lo+hi)/2;if(predicate(mid))hi=mid;else lo=mid;}return hi;};
    const uiTime=Number(ui.eventTime);
    const directTime=Number(directEvent.eventTimeMs);
    const physicalAt=t=>{const s=sampleAt(regulus,t);return s?.status==='SUPPORTED'&&Number(s?.visibility?.visibilityMarginMag)>=-1e-10;};
    const effectiveAt=t=>{const s=sampleAt(regulus,t);return s?.status==='SUPPORTED'&&Number(s?.stellar?.apparentVMagAtEye)>=spec.threshold-1e-10;};
    const qualifiedAt=t=>physicalAt(t)&&effectiveAt(t);
    const rootLo=Math.min(uiTime,directTime)-30_000;
    const rootHi=Math.max(uiTime,directTime)+30_000;
    const physicalRoot=findFalseTrue(physicalAt,rootLo,rootHi);
    const qualifiedRoot=findFalseTrue(qualifiedAt,rootLo,rootHi);
    const interval=regulus.intervalsMs?.[0]??null;
    const selectedKeys=directEvent.selected.map(e=>e.key);
    const acceptedAt=t=>candidates.filter(e=>[t,t+spec.stabilityMs/2,t+spec.stabilityMs].every(x=>qualifiesAt(e,x))).map(e=>e.key);

    return {
      spec, ui,
      atmosphereResolution:evaluation.atmosphereResolution,
      candidateCount:candidates.length,
      directEvent:{...directEvent,selectedKeys},
      deltasMs:{directMinusUi:directTime-uiTime,physicalRootMinusUi:physicalRoot==null?null:physicalRoot-uiTime,qualifiedRootMinusUi:qualifiedRoot==null?null:qualifiedRoot-uiTime,intervalStartMinusUi:interval?interval.startMs-uiTime:null,intervalStartMinusPhysicalRoot:interval&&physicalRoot!=null?interval.startMs-physicalRoot:null},
      regulus:{uiSample:compactSample(uiTime),directSample:compactSample(directTime),physicalRootSample:physicalRoot==null?null:compactSample(physicalRoot),qualifiedRootSample:qualifiedRoot==null?null:compactSample(qualifiedRoot),timelineInterval:interval,timelineResult:regulus.result},
      acceptedStableKeysAtUi:acceptedAt(uiTime),
      acceptedStableKeysAtDirect:acceptedAt(directTime),
    };
  });

  const outDir=path.join(process.env.RUNNER_TEMP,'tammuz-regulus-event-audit'); fs.mkdirSync(outDir,{recursive:true});
  fs.writeFileSync(path.join(outDir,'summary.json'),JSON.stringify({schemaVersion:1,status:'TAMMUZ_REGULUS_EVENT_CONSISTENCY_DIAGNOSTIC_COMPLETE',applicationSha:process.env.APPLICATION_SHA,audit,browserConsole,claimBoundary:{diagnosticOnly:true,noTuning:true,F314Unchanged:true,noMYSTIC:true,noPandora:true}},null,2)+'\n');
  console.log('TAMMUZ_REGULUS_AUDIT='+JSON.stringify({deltasMs:audit.deltasMs,directEvent:audit.directEvent,regulus:audit.regulus,acceptedStableKeysAtUi:audit.acceptedStableKeysAtUi}));
} finally { await browser.close(); }

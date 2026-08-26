import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const consoleLines = [];
  page.on('console', m => consoleLines.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => consoleLines.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async () => {
    const safely = (fn) => { try { return fn(); } catch (error) { return { error: String(error?.message || error) }; } };
    const summarize = value => ({ isArray:Array.isArray(value), length:Array.isArray(value)?value.length:null, first3:Array.isArray(value)?value.slice(0,3).map(r=>({name:r?.name??null,mag:r?.mag??null})):null });
    const sourceSummary = name => {
      const text = safely(() => String(eval(name)));
      if (typeof text !== 'string') return text;
      const marker = 'LEVEL-B-THREE-STAR-DIRECT-CATALOG-HANDOFF-V3';
      const at = text.indexOf(marker);
      return { length:text.length, markerAt:at, aroundMarker:at>=0?text.slice(Math.max(0,at-500),at+1800):null, hasGlobalRead:text.includes('__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__'), hasEvaluate:text.includes('evaluateSitewideRows') };
    };
    const set=(id,value)=>{const el=document.getElementById(id);if(!el)throw new Error(`missing #${id}`);el.value=String(value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));};
    try{localStorage.clear();}catch(_){ }
    if(document.getElementById('calculatorFeature'))set('calculatorFeature','three-star');
    set('lat',31.778);set('lon',35.235);set('date','2026-03-19');if(document.getElementById('timezone'))set('timezone','Asia/Jerusalem');set('observerElevationM',800);set('visibilityEngineMode','level-b-v3-crumey-blackwell-equilibrium');set('threeStarCount',3);set('threeStarMagnitudeBasis','effective');set('threeStarMagnitudeThreshold',1.7);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__='level-b-v3-crumey-blackwell-equilibrium';globalThis.__SKY_MAP_REQUEST__=true;
    if(typeof eval('ensureBuiltInCatalogReady')==='function') await eval('ensureBuiltInCatalogReady()');

    const before={catalog:summarize(globalThis.__STARS_BUILT_IN_STARS__),direct:summarize(globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__),calculate:sourceSummary('calculate'),postprocess:sourceSummary('__levelBSitewidePostprocess'),previewPostprocess:sourceSummary('__levelBSitewidePostprocessPreview'),scaffold:sourceSummary('__levelBSitewideRunUsingLegacyScaffold')};

    globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__=true;
    let producerError=null;
    try{await eval('calculate()');}catch(error){producerError=String(error?.stack||error);}
    const afterProducer={direct:summarize(globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__),catalog:summarize(globalThis.__STARS_BUILT_IN_STARS__),result:safely(()=>eval('threeStarResultData'))};
    delete globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__;

    let consumerError=null;
    try{await eval('__levelBSitewidePostprocess(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');}catch(error){consumerError=String(error?.stack||error);}
    const afterConsumer={direct:summarize(globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__),result:safely(()=>eval('threeStarResultData'))};
    delete globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__;

    return {before,producerError,afterProducer,consumerError,afterConsumer};
  });

  const output={schemaVersion:3,status:'THREE_STAR_ROW_PLUMBING_SPLIT_AUDIT',applicationSha:process.env.APPLICATION_SHA,audit,browserConsole:consoleLines,claimBoundary:{readOnlyAudit:true,noScienceParameterChange:true,noMYSTIC:true,noPandora:true}};
  const outDir=path.join(process.env.RUNNER_TEMP,'three-star-row-plumbing-audit');fs.mkdirSync(outDir,{recursive:true});fs.writeFileSync(path.join(outDir,'summary.json'),JSON.stringify(output,null,2)+'\n');
  console.log('ROW_PLUMBING_SPLIT_AUDIT='+JSON.stringify(audit));
} finally { await browser.close(); }

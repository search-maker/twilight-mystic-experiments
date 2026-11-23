import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const source=new URL('./p1_bracket_residual_interval_20261122.mjs',import.meta.url).pathname;
const mk=(day,hour='22',fraction='')=>({mode:'UNAIDED_HUMAN_DIRECT',looks:[
  ['00','NOT_SEEN'],['20','NOT_SEEN'],['40','DIRECT_SEEN'],['50','DIRECT_SEEN']
].map(([sec,status])=>({utc:day+'T'+hour+':00:'+sec+fraction+'Z',status,
clock_uncertainty_s:2,sync_method:'SYNTHETIC',cloud_direction:'CLEAR'}))});
function run(records){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p1-calendar-review-'));
 try {
  const input=path.join(dir,'input.json');
  fs.writeFileSync(input,JSON.stringify({schema:'P1-BLIND-FIELD-CANDIDATE-V1',records}));
  const p=spawnSync(process.execPath,[source,'--input',input],{encoding:'utf8'});
  assert.equal(p.status,0,p.stderr);
  return JSON.parse(p.stdout);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
}
test('native CLI must reject impossible civil dates and 24:00',()=>{
 const cases=[['2026-02-29','22'],['2026-02-30','22'],['2026-04-31','22'],
 ['2026-13-01','22'],['2026-01-00','22'],['2026-11-24','24']];
 const r=run(cases.map(([d,h])=>mk(d,h)));
 assert.equal(r.review_only_candidates,0,JSON.stringify(r));
 assert.equal(r.rejections?.CLOCK,6,JSON.stringify(r));
 assert.equal(r.actual_scientifically_admitted,0);
});
test('true leap day is only structurally admitted',()=>{
 const r=run([mk('2028-02-29')]);
 assert.equal(r.review_only_candidates,1);
 assert.equal(r.actual_scientifically_admitted,0);
 assert.equal(r.empirical_error,null);
});
test('fractional UTC on true leap day is only structurally admitted',()=>{
 const r=run([mk('2028-02-29','22','.123456')]);
 assert.equal(r.review_only_candidates,1);
 assert.equal(r.actual_scientifically_admitted,0);
});
test('preexisting 23 synthetic assertions remain green',()=>{
 const p=spawnSync(process.execPath,[source,'--self-test'],{encoding:'utf8'});
 assert.equal(p.status,0,p.stderr);
 const r=JSON.parse(p.stdout);
 assert.equal(r.synthetic_assertions_passed,23);
 assert.equal(r.actual_human_first_sightings,0);
});

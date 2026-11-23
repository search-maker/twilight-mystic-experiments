#!/usr/bin/env node
// P1-FVS-20261122-R0 / REVIEW ONLY: interval-censored human onset bounds.
// No approved study, no human outcome record, no scientific model-error claim.
import assert from 'node:assert/strict';
import fs from 'node:fs';

// UTC lexical form alone is insufficient: Date.parse normalizes impossible civil days.
// Require a finite parsed instant whose UTC calendar seconds round-trip unchanged.
const clock = (s) => {
  if (typeof s !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(s)) return NaN;
  const t = Date.parse(s);
  if (!Number.isFinite(t)) return NaN;
  return new Date(t).toISOString().slice(0, 19) === s.slice(0, 19) ? t : NaN;
};
const refuse = (reason) => ({kind:'REFUSED', reason, scientific_admission:false, model_error:null});
export function humanBracket(r) {
  if (r?.mode !== 'UNAIDED_HUMAN_DIRECT' || !Array.isArray(r.looks) || r.looks.length < 4 || r.looks.length > 300)
    return refuse('NOT_BOUNDED_UNAIDED_HUMAN_LOOKS');
  const looks = r.looks;
  let previous = -Infinity;
  const times = [];
  for (const look of looks) {
    const t = clock(look.utc);
    if (!Number.isFinite(t) || t <= previous || typeof look.clock_uncertainty_s !== 'number' ||
        !Number.isFinite(look.clock_uncertainty_s) || look.clock_uncertainty_s < 0 ||
        look.clock_uncertainty_s > 5 || !look.sync_method) return refuse('CLOCK');
    if (look.cloud_direction !== 'CLEAR') return refuse('DIRECTIONAL_CLOUD');
    previous = t; times.push(t);
  }
  const firstYes = looks.findIndex(l => l.status === 'DIRECT_SEEN');
  if (firstYes < 2) return refuse('NO_DIRECT_YES_AFTER_TWO_PREVIOUS_LOOKS');
  const previousNoIndices = looks.slice(0,firstYes).map((l,i)=>l.status === 'NOT_SEEN' ? i : -1).filter(i=>i>=0);
  if (previousNoIndices.length < 2) return refuse('MISSING_TWO_PRIOR_NONDETECTIONS');
  const lastNo = previousNoIndices.at(-1);
  if (looks.slice(lastNo+1,firstYes).some(l => l.status !== 'NOT_SEEN')) return refuse('AMBIGUOUS_GAP');
  const confirmation = looks.findIndex((l,i)=>i>firstYes && l.status === 'DIRECT_SEEN');
  if (confirmation < 0 || times[confirmation]-times[firstYes]>120000 ||
      looks.slice(firstYes+1,confirmation).some(l=>l.status!=='DIRECT_SEEN'))
    return refuse('NO_PROMPT_DIRECT_CONFIRMATION');
  if (times[firstYes]-times[lastNo] > 120000) return refuse('BRACKET_OVER_120_SECONDS');
  const noLo = times[lastNo]-looks[lastNo].clock_uncertainty_s*1000;
  const noHi = times[lastNo]+looks[lastNo].clock_uncertainty_s*1000;
  const yesLo = times[firstYes]-looks[firstYes].clock_uncertainty_s*1000;
  const yesHi = times[firstYes]+looks[firstYes].clock_uncertainty_s*1000;
  if (noHi>=yesLo) return refuse('CLOCK_ORDER_UNCERTAIN');
  return {kind:'STRUCTURAL_BRACKET_ONLY',lower_utc:new Date(noLo).toISOString(),
    upper_utc:new Date(yesHi).toISOString(),width_s:(yesHi-noLo)/1000,
    last_no_index:lastNo,first_yes_index:firstYes,confirmation_index:confirmation,
    scientific_admission:false,model_error:null};
}
export function candidateResidual(bracket, prediction) {
  if(bracket?.kind !== 'STRUCTURAL_BRACKET_ONLY') return refuse('NO_HUMAN_BRACKET');
  if(!prediction || prediction.type === 'UNSUPPORTED_NULL')
    return {kind:'UNSUPPORTED_NULL',residual_s:null,scientific_admission:false};
  if(prediction.type !== 'CANDIDATE_INTERVAL') return refuse('PREDICTION_UNFROZEN');
  const a=clock(bracket.lower_utc),b=clock(bracket.upper_utc);
  const c=clock(prediction.lower_utc),d=clock(prediction.upper_utc);
  if(![a,b,c,d].every(Number.isFinite) || !(a<b&&c<=d)) return refuse('INVALID_INTERVAL');
  const lo=(a-d)/1000,hi=(b-c)/1000;
  return {kind:'SYNTHETIC_MATH_NOT_EMPIRICAL_ERROR',residual_s:[lo,hi],
    abs_error_possible_min_s:(lo<=0&&hi>=0)?0:Math.min(Math.abs(lo),Math.abs(hi)),
    abs_error_possible_max_s:Math.max(Math.abs(lo),Math.abs(hi)),
    possibly_overlaps:a<=d&&b>=c,
    prediction_guaranteed_contains_bracket:c<=a&&b<=d,
    scientific_admission:false,model_error:null};
}
function selfTest() {
  const L=(sec,status,u=2,cloud='CLEAR')=>({utc:'2026-11-24T22:00:'+String(sec).padStart(2,'0')+'Z',
    status,clock_uncertainty_s:u,sync_method:'SYNTHETIC',cloud_direction:cloud});
  const base={mode:'UNAIDED_HUMAN_DIRECT',looks:[L(0,'NOT_SEEN'),L(20,'NOT_SEEN'),L(40,'DIRECT_SEEN',3),L(50,'DIRECT_SEEN')]};
  const b=humanBracket(base);let tests=0;
  const eq=(a,e)=>{assert.deepEqual(a,e);tests++;};
  eq(b.kind,'STRUCTURAL_BRACKET_ONLY');eq(b.width_s,25);
  eq(b.lower_utc,'2026-11-24T22:00:18.000Z');eq(b.upper_utc,'2026-11-24T22:00:43.000Z');
  eq(b.scientific_admission,false);eq(b.model_error,null);
  const p={type:'CANDIDATE_INTERVAL',lower_utc:'2026-11-24T22:00:30Z',upper_utc:'2026-11-24T22:00:35Z'};
  const c=candidateResidual(b,p);eq(c.residual_s,[-17,13]);eq(c.abs_error_possible_min_s,0);
  eq(c.abs_error_possible_max_s,17);eq(c.possibly_overlaps,true);
  eq(c.prediction_guaranteed_contains_bracket,false);
  eq(candidateResidual(b,{type:'UNSUPPORTED_NULL'}).residual_s,null);
  const q={type:'CANDIDATE_INTERVAL',lower_utc:'2026-11-24T22:01:00Z',upper_utc:'2026-11-24T22:01:00Z'};
  eq(candidateResidual(b,q).abs_error_possible_min_s,17);eq(candidateResidual(b,q).abs_error_possible_max_s,42);
  eq(humanBracket({...base,mode:'ZENITH_SQM'}).reason,'NOT_BOUNDED_UNAIDED_HUMAN_LOOKS');
  eq(humanBracket({...base,looks:[L(0,'NOT_SEEN'),L(20,'POSSIBLE'),L(40,'DIRECT_SEEN'),L(50,'DIRECT_SEEN')]}).reason,'MISSING_TWO_PRIOR_NONDETECTIONS');
  eq(humanBracket({...base,looks:[L(0,'NOT_SEEN'),L(20,'NOT_SEEN'),L(30,'POSSIBLE'),L(40,'DIRECT_SEEN'),L(50,'DIRECT_SEEN')]}).reason,'AMBIGUOUS_GAP');
  eq(humanBracket({...base,looks:[L(0,'NOT_SEEN'),L(20,'NOT_SEEN'),L(40,'DIRECT_SEEN'),L(50,'DIRECT_SEEN',2,'UNKNOWN')]}).reason,'DIRECTIONAL_CLOUD');
  eq(humanBracket({...base,looks:[L(0,'NOT_SEEN'),L(20,'NOT_SEEN',5),L(21,'DIRECT_SEEN',5),L(40,'DIRECT_SEEN')]}).reason,'CLOCK_ORDER_UNCERTAIN');
  eq(humanBracket({...base,looks:[L(0,'NOT_SEEN'),L(20,'NOT_SEEN'),L(40,'DIRECT_SEEN'),L(50,'NOT_CHECKED')]}).reason,'NO_PROMPT_DIRECT_CONFIRMATION');
  eq(candidateResidual(null,p).reason,'NO_HUMAN_BRACKET');
  eq(c.scientific_admission,false);eq(c.model_error,null);
  console.log(JSON.stringify({synthetic_assertions_passed:tests,actual_human_first_sightings:0,
    actual_model_residuals:null,late_sun_depression_10_5_to_16:'UNSUPPORTED_NULL',
    scientific_admission:'NO_PREREGISTRATION_OR_MODEL_SHA_APPROVED'},null,2));
}
if(process.argv[2]==='--self-test')selfTest();
else if(process.argv[2]==='--input' && process.argv[3]) {
  const st=fs.statSync(process.argv[3]);if(st.size>256000)throw Error('INPUT_TOO_LARGE');
  const v=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
  if(v.schema!=='P1-BLIND-FIELD-CANDIDATE-V1'||!Array.isArray(v.records)||v.records.length>144)throw Error('UNBOUNDED_OR_WRONG_INPUT');
  let candidate=0;const rejected={};
  for(const r of v.records){const b=humanBracket(r);if(b.kind==='STRUCTURAL_BRACKET_ONLY')candidate++;else rejected[b.reason]=(rejected[b.reason]||0)+1;}
  console.log(JSON.stringify({review_only_candidates:candidate,rejections:rejected,actual_scientifically_admitted:0,
    empirical_error:null,model_sha:null,reason:'UNAPPROVED_BLIND_CUSTODY_AND_PREDICTION_LOCK'},null,2));
} else throw Error('Usage: --self-test | --input file.json');

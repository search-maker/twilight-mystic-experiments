#!/usr/bin/env node
// P1-FVS-20261122-R0 PRE-OUTCOME REVIEW: empirical input availability and prediction blinding.
// No actual observer records, numerical sky predictions, science approval, or model errors.
import assert from 'node:assert/strict';

const iso = (s) => {
  if (typeof s !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(s)) return NaN;
  const n=Date.parse(s);
  return Number.isFinite(n) ? n : NaN;
};

export function chronology(c) {
  const refusal=(reason)=>({chronology:'REFUSE',reason,scientific_admission:false,first_visibility_errors:null});
  if (!c || !['EX_ANTE','OUTCOME_BLIND_HINDCAST'].includes(c.arm)) return refusal('UNDECLARED_ARM');
  const keys=['first_look_utc','model_lock_utc','source_qc_rule_lock_utc','case_selection_lock_utc','input_acquired_utc','prediction_sealed_utc','raw_log_lock_utc','outcomes_unblinded_utc'];
  const t={}; for(const k of keys){ t[k]=iso(c[k]); if(!Number.isFinite(t[k])) return refusal('MISSING_OR_BAD_CLOCK_'+k); }
  const first=t.first_look_utc;
  if (t.model_lock_utc>=first || t.source_qc_rule_lock_utc>=first || t.case_selection_lock_utc>=first)
    return refusal('MODEL_INPUT_SOURCE_OR_CASE_RULE_WAS_NOT_LOCKED_BEFORE_LOOK');
  if (typeof c.source_qc_rule_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(c.source_qc_rule_sha256))
    return refusal('NO_PREDECLARED_SOURCE_QC_RECEIPT');
  if (c.predicted_sun_depth_deg !== null && !(typeof c.predicted_sun_depth_deg==='number' && Number.isFinite(c.predicted_sun_depth_deg)))
    return refusal('UNBOUNDED_OR_INVALID_DOMAIN');
  if (c.predicted_sun_depth_deg !== null && c.predicted_sun_depth_deg>10.5 && c.predicted_sun_depth_deg<=16 && c.prediction_value_type !== 'UNSUPPORTED_NULL')
    return refusal('P1_LATE_DOMAIN_NUMERIC_UNSUPPORTED');
  if (c.prediction_value_type !== 'UNSUPPORTED_NULL' && c.prediction_value_type !== 'CANDIDATE_INTERVAL')
    return refusal('INVALID_PREDICTION_VALUE_TYPE');
  if (t.input_acquired_utc>t.prediction_sealed_utc)
    return refusal('INPUT_ACQUIRED_AFTER_PREDICTION');
  if (t.raw_log_lock_utc<t.first_look_utc)
    return refusal('RAW_LOCK_BEFORE_FIRST_LOOK');
  if (t.outcomes_unblinded_utc<=t.raw_log_lock_utc)
    return refusal('OUTCOME_UNBLIND_BEFORE_RAW_LOCK');
  if (c.arm==='EX_ANTE') {
    if (t.prediction_sealed_utc>=first)
      return refusal('EX_ANTE_PREDICTION_NOT_SEALED_BEFORE_FIRST_LOOK');
    if (t.input_acquired_utc>=first)
      return refusal('EX_ANTE_INPUT_NOT_AVAILABLE_BEFORE_FIRST_LOOK');
  } else {
    if (t.prediction_sealed_utc<=t.raw_log_lock_utc)
      return refusal('HINDCAST_PREDICTION_BEFORE_RAW_LOCK');
    if (t.prediction_sealed_utc>=t.outcomes_unblinded_utc)
      return refusal('HINDCAST_PREDICTION_AFTER_UNBLINDING');
    if (c.outcome_blinded_to_modeler !== true || c.source_selection_independent_of_sightings !== true)
      return refusal('OUTCOME_BLINDNESS_OR_SOURCE_SELECTION_NOT_ATTESTED');
  }
  return {chronology:'CANDIDATE_SEQUENCE_ONLY',reason:'INDEPENDENT_CUSTODY_AND_SCIENCE_APPROVAL_STILL_REQUIRED',
    arm:c.arm,scientific_admission:false,first_visibility_errors:null,
    temporal_claim:c.arm==='EX_ANTE'?'PRE_LOOK_INPUT_AND_PREDICTION':'POST_RAW_LOCK_BLIND_HINDCAST_NOT_A_FORECAST'};
}

function selfTest() {
  const h='a'.repeat(64);
  const base={arm:'EX_ANTE',model_lock_utc:'2026-11-23T20:00:00Z',source_qc_rule_lock_utc:'2026-11-23T20:01:00Z',case_selection_lock_utc:'2026-11-23T20:02:00Z',source_qc_rule_sha256:h,
    input_acquired_utc:'2026-11-23T20:40:00Z',prediction_sealed_utc:'2026-11-23T20:50:00Z',first_look_utc:'2026-11-23T21:00:00Z',raw_log_lock_utc:'2026-11-23T21:30:00Z',outcomes_unblinded_utc:'2026-11-23T22:00:00Z',predicted_sun_depth_deg:8,prediction_value_type:'CANDIDATE_INTERVAL',outcome_blinded_to_modeler:true,source_selection_independent_of_sightings:true};
  let passed=0;
  const yes=(x,arm)=>{let v=chronology(x);assert.equal(v.chronology,'CANDIDATE_SEQUENCE_ONLY',v.reason);assert.equal(v.arm,arm);assert.equal(v.scientific_admission,false);assert.equal(v.first_visibility_errors,null);passed++;};
  const no=(x,reason)=>{let v=chronology(x);assert.equal(v.reason,reason);assert.equal(v.scientific_admission,false);passed++;};
  yes(base,'EX_ANTE');
  no({...base,input_acquired_utc:'2026-11-23T21:15:00Z',prediction_sealed_utc:'2026-11-23T21:20:00Z'},'EX_ANTE_PREDICTION_NOT_SEALED_BEFORE_FIRST_LOOK');
  no({...base,prediction_sealed_utc:'2026-11-23T20:50:00Z',input_acquired_utc:'2026-11-23T21:15:00Z'},'INPUT_ACQUIRED_AFTER_PREDICTION');
  no({...base,case_selection_lock_utc:'2026-11-23T21:00:00Z'},'MODEL_INPUT_SOURCE_OR_CASE_RULE_WAS_NOT_LOCKED_BEFORE_LOOK');
  no({...base,source_qc_rule_sha256:null},'NO_PREDECLARED_SOURCE_QC_RECEIPT');
  no({...base,predicted_sun_depth_deg:12},'P1_LATE_DOMAIN_NUMERIC_UNSUPPORTED');
  yes({...base,predicted_sun_depth_deg:12,prediction_value_type:'UNSUPPORTED_NULL'},'EX_ANTE');
  const hind={...base,arm:'OUTCOME_BLIND_HINDCAST',input_acquired_utc:'2026-11-23T21:45:00Z',prediction_sealed_utc:'2026-11-23T21:50:00Z'};
  yes(hind,'OUTCOME_BLIND_HINDCAST');
  no({...hind,prediction_sealed_utc:'2026-11-23T21:25:00Z',input_acquired_utc:'2026-11-23T21:20:00Z'},'HINDCAST_PREDICTION_BEFORE_RAW_LOCK');
  no({...hind,prediction_sealed_utc:'2026-11-23T22:10:00Z',input_acquired_utc:'2026-11-23T21:40:00Z'},'HINDCAST_PREDICTION_AFTER_UNBLINDING');
  no({...hind,outcome_blinded_to_modeler:false},'OUTCOME_BLINDNESS_OR_SOURCE_SELECTION_NOT_ATTESTED');
  no({...hind,source_selection_independent_of_sightings:false},'OUTCOME_BLINDNESS_OR_SOURCE_SELECTION_NOT_ATTESTED');
  no({...base,raw_log_lock_utc:'2026-11-23T20:59:00Z'},'RAW_LOCK_BEFORE_FIRST_LOOK');
  assert.equal(passed,13);
  console.log(JSON.stringify({synthetic_controls_passed:passed,real_observations:0,empirical_first_visibility_errors:null,late_degrees:'UNSUPPORTED_NULL',status:'REVIEW_ONLY_NOT_APPROVED'},null,2));
}
if(process.argv[2]==='--self-test') selfTest();
else if(process.argv.length===2) console.log('Usage: node p1_input_chronology_20261122.mjs --self-test');
else throw Error('UNKNOWN_ARG');

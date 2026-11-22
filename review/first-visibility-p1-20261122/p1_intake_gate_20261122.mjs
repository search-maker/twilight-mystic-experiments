#!/usr/bin/env node
// P1-FVS-20261122-R0: bounded PRE-ADMISSION evidence screen.
// This is NOT model validation, preregistration approval, or a prediction engine.
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const SHA = /^[0-9a-f]{64}$/;
const MODEL_SHA = /^[0-9a-f]{40}$/;
const MAX_BYTES = 2_000_000;
const MAX_RECORDS = 500;
const MAX_LOOKS_PER_RECORD = 300;
const ALLOWED = new Set(['NOT_SEEN','POSSIBLE','AVERTED_SEEN','DIRECT_SEEN','CLOUD_OBSCURED','NOT_CHECKED']);
const isSha = s => typeof s === 'string' && SHA.test(s);
const finite = n => typeof n === 'number' && Number.isFinite(n);
const readBounded = path => {
  const size = fs.statSync(path).size;
  if (size > MAX_BYTES) throw Error('INPUT_TOO_LARGE');
  const bytes = fs.readFileSync(path);
  return {data:JSON.parse(bytes.toString('utf8')),sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
};
const utc = x => {
  if (typeof x !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(x)) return NaN;
  const n = Date.parse(x);
  return Number.isFinite(n) ? n : NaN;
};
const assessLook = l => {
  if (!l || !ALLOWED.has(l.status) || !l.timestamp ||
      !Number.isFinite(utc(l.timestamp.utc)) ||
      !finite(l.timestamp.uncertainty_seconds) ||
      l.timestamp.uncertainty_seconds < 0 || l.timestamp.uncertainty_seconds > 5 ||
      typeof l.timestamp.sync_method !== 'string' || !l.timestamp.sync_method.trim()) return 'CLOCK_OR_STATUS';
  if (!finite(l.star_alt_deg) || l.star_alt_deg < 20 || l.star_alt_deg > 80 ||
      !finite(l.star_az_deg) || l.star_az_deg < 0 || l.star_az_deg >= 360 ||
      !finite(l.sun_depth_deg) || l.sun_depth_deg < 2 || l.sun_depth_deg > 16) return 'GEOMETRY';
  if (!finite(l.adapted_minutes) || l.adapted_minutes < 0 || !finite(l.screen_light_seconds_last_15m) || l.screen_light_seconds_last_15m < 0) return 'ADAPTATION_METADATA';
  if (l.cloud_direction !== 'CLEAR') return 'DIRECTIONAL_CLOUD_OR_UNKNOWN';
  return null;
};
function candidate(r, attempts) {
  if (!r || !r.record_id || !r.attempt_id) return 'INVALID_RECORD_ID';
  if (r.outcome_admission !== 'BRACKET_QUALIFIED') return 'PREDECLARED_REJECTION_OR_UNREVIEWED';
  if (!isSha(r.site_private_metadata_sha256) || !isSha(r.consent_receipt_private_sha256) || !isSha(r.source_log_sha256)) return 'PRIVATE_ORIGINAL_CUSTODY_MISSING';
  const a = attempts.get(r.attempt_id);
  if (!a || a.status !== 'COMPLETED' || a.site_id !== r.site_id || a.observer_id !== r.observer_id || a.night_local !== r.night_local || a.original_log_sha256 !== r.source_log_sha256) return 'ATTEMPT_OR_RAW_LOG_MISMATCH';
  if (!Number.isInteger(r.hip) || r.hip <= 0 || !finite(r.v_mag) || r.v_mag < -2 || r.v_mag > 5.5) return 'CATALOGUE';
  if (!r.weather || !finite(r.weather.directional_horizon_alt_deg) || r.weather.directional_horizon_alt_deg < 0 || r.weather.directional_horizon_alt_deg > 90 || !Array.isArray(r.look_events) || r.look_events.length > MAX_LOOKS_PER_RECORD) return 'HORIZON_OR_LOOK_ARRAY';
  if (r.look_events.length < 4) return 'TOO_FEW_LOOKS';
  const ev = r.look_events;
  let previous = -Infinity;
  for (const l of ev) {
    const problem = assessLook(l);
    if (problem) return problem;
    const t = utc(l.timestamp.utc);
    if (t <= previous) return 'NONMONOTONIC_CLOCK';
    previous = t;
    if (l.star_alt_deg <= r.weather.directional_horizon_alt_deg) return 'OBSTRUCTED_HORIZON';
  }
  const first = ev.findIndex(l => l.status === 'DIRECT_SEEN');
  if (first < 2) return 'NO_FIRST_DIRECT_OR_TWO_PRIOR';
  const lastNo = ev.slice(0,first).map((l,i) => l.status === 'NOT_SEEN' ? i : -1).filter(x => x >= 0).at(-1);
  if (lastNo === undefined) return 'NO_PRIOR_TRUE_NONDETECTION';
  const prior = ev.slice(0,lastNo+1).filter(l => l.status === 'NOT_SEEN');
  if (prior.length < 2) return 'LESS_THAN_TWO_NOT_SEEN';
  if (ev.slice(lastNo+1,first).some(l => l.status !== 'NOT_SEEN')) return 'AMBIGUOUS_GAP';
  const width = (utc(ev[first].timestamp.utc)-utc(ev[lastNo].timestamp.utc))/1000;
  if (!(width > 0 && width <= 120)) return 'BRACKET_GT_120S';
  const confirmation = ev.slice(first+1).find(l => l.status === 'DIRECT_SEEN');
  if (!confirmation || (utc(confirmation.timestamp.utc)-utc(ev[first].timestamp.utc)) > 120000 ||
      ev.slice(first+1,ev.indexOf(confirmation)).some(l => l.status !== 'DIRECT_SEEN')) return 'NO_DIRECT_CONFIRMATION';
  if (r.skyglow?.status === 'MEASURED' && (!finite(r.skyglow.value) || !r.skyglow.units || !finite(r.skyglow.view_alt_deg) || !finite(r.skyglow.view_az_deg) || !finite(r.skyglow.fov_deg) || r.skyglow.fov_deg <= 0 || r.skyglow.view_alt_deg < 0 || r.skyglow.view_alt_deg > 90 || r.skyglow.view_az_deg < 0 || r.skyglow.view_az_deg >= 360 || !isSha(r.skyglow.calibration_sha256))) return 'CLAIMED_SKYGLOW_NOT_DOCUMENTED';
  if (r.aerosol?.qc === 'PASS' && (!finite(r.aerosol.aod550) || r.aerosol.aod550 < 0 || !Number.isFinite(utc(r.aerosol.utc)) || !isSha(r.aerosol.source_sha256))) return 'CLAIMED_AOD_PASS_NOT_DOCUMENTED';
  return null;
}
function evaluate(m) {
  const blockers = [];
  if (m?.manifest_version === 'HUMAN-PUBLISHED-ANCHORS-20261122-R0') {
    return {input_type:'PUBLISHED_RETROSPECTIVE_NOT_BLIND',record_count:m.records?.length||0,
      candidate_brackets:0,scientifically_admitted_brackets:0,model_error_computed:false,
      historic_low_altitude_rows:(m.records||[]).filter(x=>finite(x.star_altitude_deg_article)&&x.star_altitude_deg_article<20).length,
      blockers:['RETROSPECTIVE_AUTHORS_FIT','NO_ORIGINAL_TRUE_NOT_SEEN_TO_DIRECT_SEEN_SEQUENCE','NO_SOURCE_TIMED_CONFIRMATION','NO_QUALIFIED_PRE_OUTCOME_MODEL_LOCK']};
  }
  if (m?.protocol_id !== 'P1-FVS-20261122-R0') throw Error('WRONG_PROTOCOL');
  if (!Array.isArray(m.records) || !Array.isArray(m.attempts) || m.records.length > MAX_RECORDS || m.attempts.length > MAX_RECORDS) throw Error('INVALID_OR_UNBOUNDED_ARRAY');
  if (m.protocol_status !== 'RAW_LOCKED_PENDING_UNBLIND' && m.protocol_status !== 'UNBLINDED_ANALYSIS') blockers.push('PROTOCOL_NOT_RAW_LOCKED');
  if (!MODEL_SHA.test(m.model_sha||'')) blockers.push('NO_FROZEN_QUALIFIED_MODEL_SHA');
  if (!isSha(m.source_manifest?.catalog_sha256) || !isSha(m.source_manifest?.ephemeris_sha256) || !isSha(m.source_manifest?.atmosphere_manifest_sha256)) blockers.push('UNVERIFIED_CATALOGUE_EPHEMERIS_ATMOSPHERE_HASHES');
  if (m.source_manifest?.access_permission !== 'PERMITTED') blockers.push('SOURCE_ACCESS_NOT_PERMITTED');
  // An independent audit of blinded commitments/site and case locks is ALWAYS necessary.
  blockers.push('INDEPENDENT_PREOUTCOME_LOCK_AND_CUSTODY_REVIEW_NOT_MACHINE_VERIFIED');
  const attempts = new Map();
  for (const a of m.attempts) { if (attempts.has(a.attempt_id)) throw Error('DUPLICATE_ATTEMPT_ID'); attempts.set(a.attempt_id,a); }
  const reasons = {};
  const seen = new Set();
  let candidateCount=0;
  for (const r of m.records) {
    if (seen.has(r.record_id)) throw Error('DUPLICATE_RECORD_ID'); seen.add(r.record_id);
    const reason=m.has_real_observer_data !== true ? 'NO_REAL_OBSERVER_DATA_DECLARED' : candidate(r,attempts);
    if (!reason) candidateCount++;
    else reasons[reason]=(reasons[reason]||0)+1;
  }
  return {input_type:'P1_ORIGINAL_EVENT_MANIFEST',record_count:m.records.length,attempted_sessions:m.attempts.length,
    possible_human_brackets_before_independent_review:candidateCount,
    scientifically_admitted_brackets:0,model_error_computed:false,blocking_gates:blockers,
    rejection_reason_counts:reasons,
    physical_measurements_authentication:'NOT_EVALUATED; ZENITH PHOTOMETRY IS NOT HUMAN SEEING OR DIRECTIONAL SPECTRAL RADIANCE'};
}
function selfTest() {
  const blank={protocol_id:'P1-FVS-20261122-R0',protocol_status:'REVIEW_DRAFT_NO_ENROLLMENT',model_sha:null,has_real_observer_data:false,
    source_manifest:{catalog_sha256:null,ephemeris_sha256:null,atmosphere_manifest_sha256:null,access_permission:'UNVERIFIED'},records:[],attempts:[]};
  const b=evaluate(blank);assert.equal(b.scientifically_admitted_brackets,0);assert.equal(b.possible_human_brackets_before_independent_review,0);
  const h='a'.repeat(64), sha='b'.repeat(40);
  const look=(sec,status,options={})=>({timestamp:{utc:'2026-11-24T22:00:'+String(sec).padStart(2,'0')+'Z',uncertainty_seconds:2,sync_method:'SYNTHETIC'},status,star_alt_deg:35,star_az_deg:130,sun_depth_deg:11,cloud_direction:'CLEAR',adapted_minutes:15,screen_light_seconds_last_15m:0,...options});
  const baseR={record_id:'SYNTHETIC',attempt_id:'A',site_id:'SITE',observer_id:'OBSERVER',night_local:'2026-11-24',hip:1,v_mag:4.5,
    site_private_metadata_sha256:h,consent_receipt_private_sha256:h,source_log_sha256:h,
    weather:{directional_horizon_alt_deg:5},skyglow:{status:'UNKNOWN'},aerosol:{qc:'UNKNOWN'},
    look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN'),look(50,'DIRECT_SEEN')],outcome_admission:'BRACKET_QUALIFIED'};
  const attempts=new Map([['A',{attempt_id:'A',status:'COMPLETED',site_id:'SITE',observer_id:'OBSERVER',night_local:'2026-11-24',original_log_sha256:h}]]);
  assert.equal(candidate(baseR,attempts),null);
  assert.equal(candidate({...baseR,outcome_admission:'REJECT_CONSENT'},attempts),'PREDECLARED_REJECTION_OR_UNREVIEWED');
  assert.equal(candidate({...baseR,outcome_admission:'UNREVIEWED'},attempts),'PREDECLARED_REJECTION_OR_UNREVIEWED');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN',{adapted_minutes:-1}),look(50,'DIRECT_SEEN')]},attempts),'ADAPTATION_METADATA');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN',{screen_light_seconds_last_15m:-1}),look(50,'DIRECT_SEEN')]},attempts),'ADAPTATION_METADATA');
  assert.equal(candidate({...baseR,aerosol:{qc:'PASS',aod550:-0.1,utc:'2026-11-24T22:00:42Z',source_sha256:h}},attempts),'CLAIMED_AOD_PASS_NOT_DOCUMENTED');
  assert.equal(candidate({...baseR,skyglow:{status:'MEASURED',value:1,units:'cd/m2',view_alt_deg:35,view_az_deg:130,fov_deg:-1,calibration_sha256:h}},attempts),'CLAIMED_SKYGLOW_NOT_DOCUMENTED');
  assert.equal(candidate({...baseR,weather:{directional_horizon_alt_deg:-3}},attempts),'HORIZON_OR_LOOK_ARRAY');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(30,'POSSIBLE'),look(40,'DIRECT_SEEN'),look(50,'DIRECT_SEEN')]},attempts),'AMBIGUOUS_GAP');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN'),look(50,'DIRECT_SEEN',{cloud_direction:'OPAQUE'})]},attempts),'DIRECTIONAL_CLOUD_OR_UNKNOWN');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN'),look(50,'DIRECT_SEEN',{timestamp:{utc:'2026-11-24T22:00:50Z',uncertainty_seconds:10,sync_method:'SYNTHETIC'}})]},attempts),'CLOCK_OR_STATUS');
  assert.equal(candidate({...baseR,look_events:[look(0,'NOT_SEEN'),look(20,'NOT_SEEN'),look(40,'DIRECT_SEEN')]},attempts),'TOO_FEW_LOOKS');
  assert.equal(candidate({...baseR,source_log_sha256:null},attempts),'PRIVATE_ORIGINAL_CUSTODY_MISSING');
  assert.equal(candidate({...baseR,skyglow:{status:'MEASURED',value:null,units:null}},attempts),'CLAIMED_SKYGLOW_NOT_DOCUMENTED');
  assert.equal(candidate({...baseR,aerosol:{qc:'PASS',aod550:null}},attempts),'CLAIMED_AOD_PASS_NOT_DOCUMENTED');
  const q={...blank,protocol_status:'RAW_LOCKED_PENDING_UNBLIND',model_sha:sha,has_real_observer_data:true,
    source_manifest:{catalog_sha256:h,ephemeris_sha256:h,atmosphere_manifest_sha256:h,access_permission:'PERMITTED'},records:[baseR],attempts:[...attempts.values()]};
  const out=evaluate(q);assert.equal(out.possible_human_brackets_before_independent_review,1);assert.equal(out.scientifically_admitted_brackets,0);
  assert.equal(evaluate({...q,has_real_observer_data:false}).possible_human_brackets_before_independent_review,0);
  const qMissingObserver={...q};delete qMissingObserver.has_real_observer_data;
  assert.equal(evaluate(qMissingObserver).possible_human_brackets_before_independent_review,0);
  assert.equal(evaluate({manifest_version:'HUMAN-PUBLISHED-ANCHORS-20261122-R0',records:[{star_altitude_deg_article:13},{star_altitude_deg_article:12},{star_altitude_deg_article:28},{star_altitude_deg_article:null}]}).historic_low_altitude_rows,2);
  console.log('SYNTHETIC_SELF_TEST 20/20 PASS; scientific evidence admitted: 0; model errors: NOT COMPUTED');
}
if(process.argv[2]==='--self-test') selfTest();
else if(process.argv.length===3) {const {data,sha256}=readBounded(process.argv[2]); console.log(JSON.stringify({input_sha256:sha256,...evaluate(data)},null,2));}
else {console.error('Usage: node p1_intake_gate_20261122.mjs <P1-or-historical-JSON> | --self-test');process.exitCode=2;}

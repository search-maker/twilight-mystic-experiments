// P1 candidate attention sidecar. NO empirical records, NO scientific model approval.
// Parent schema/validator f5b5b32dc5463e3226dccda34b85d63c89bf0f26.
// Must be used in addition to the existing event, custody, freeze and atmosphere gates.
// Each look records observed start/end UTC, exact assigned target, attention, gaze,
// target/horizon clearance, interruptions and bright-light exposures since previous.
// Positive dwell only: minimum effective dwell is UNSET pending prospective review.
// Unknown and non-direct observations are retained separately, not silently discarded.
// This is a method proposal; do not collect or score outcomes before approval.
function attention(record,sidecar) {
 const fail=(reason)=>({eligible:false,reason,model_error_seconds:null});
 if(!record||!sidecar||sidecar.event_id!==record.event_id||sidecar.assigned_target!==record.target_catalog_id||sidecar.raw_sha256!==record.raw_sha256||!(/^[a-f0-9]{64}$/.test(record.raw_sha256??"")))return fail("IDENTITY_OR_RAW_DIGEST_MISMATCH");
 if(!Array.isArray(record.checks)||!Array.isArray(sidecar.looks)||record.checks.length!==sidecar.looks.length||record.checks.length<3)return fail("INCOMPLETE_LOOK_LOG");
 const ts=s=>typeof s==="string"&&s.endsWith("Z")?Date.parse(s):NaN;
 let priorEnd=-Infinity; const adapt=ts(record.adaptation_started_utc);
 if(!Number.isFinite(adapt))return fail("ADAPTATION_UNKNOWN");
 let firstYes=-1, lastNo=-1;
 for(let i=0;i<record.checks.length;i++){
  const e=record.checks[i], l=sidecar.looks[i], start=ts(l?.start_utc),end=ts(l?.end_utc);
  if(!l||!Number.isFinite(start)||!Number.isFinite(end)||end<=start||start<priorEnd||end!==ts(e.utc))return fail("INVALID_DWELL_OR_CHECK_LINK");
  if(i===0&&start-adapt<600000)return fail("ADAPTATION_BEFORE_LOOK_LT_600S");
  if(l.target!==record.target_catalog_id||l.attention!=="TARGET_DIRECTED"||l.gaze!=="DIRECT"||e.visual_aid!=="NONE")return fail("NOT_SAME_DIRECT_UNAIDED_TARGET");
  if(l.target_clear!==true||l.horizon_clear!==true||l.interruption_since_previous!==false||l.bright_light_exposure_since_previous!==false)return fail("CONDITIONS_NOT_CONTINUOUSLY_ELIGIBLE");
  if(!["NO","YES","CONFIRM"].includes(e.state))return fail("UNKNOWN_CHECK_STATE");
  if(firstYes===-1){if(e.state==="NO")lastNo=i;else if(e.state==="YES"){if(lastNo<0)return fail("LEFT_CENSORED");firstYes=i;}else return fail("CONFIRM_WITHOUT_YES");}
  else if(i===firstYes+1){if(e.state!=="CONFIRM")return fail("FIRST_YES_NOT_CONFIRMED");}
  priorEnd=end;
 }
 if(firstYes<0||firstYes+1>=record.checks.length)return fail("RIGHT_CENSORED_OR_UNCONFIRMED");
 const a=ts(record.checks[lastNo].utc),b=ts(record.checks[firstYes].utc),c=ts(record.checks[firstYes+1].utc);
 if(b<=a||b-a>60000||c<=b||c-b>60000)return fail("BRACKET_OR_CONFIRMATION_WIDTH_INVALID");
 return {eligible:true,last_no_utc:record.checks[lastNo].utc,first_yes_utc:record.checks[firstYes].utc,confirmation_utc:record.checks[firstYes+1].utc,model_error_seconds:null};
}
function selftest(){
 const record={event_id:"SYNTHETIC_ONLY",target_catalog_id:"HIP-1",raw_sha256:"0".repeat(64),adaptation_started_utc:"2026-12-01T22:00:00Z",checks:[{utc:"2026-12-01T22:12:00Z",state:"NO",visual_aid:"NONE"},{utc:"2026-12-01T22:12:25Z",state:"YES",visual_aid:"NONE"},{utc:"2026-12-01T22:12:50Z",state:"CONFIRM",visual_aid:"NONE"}]};
 const sidecar={event_id:record.event_id,assigned_target:record.target_catalog_id,raw_sha256:record.raw_sha256,looks:record.checks.map((e,i)=>({start_utc:["2026-12-01T22:11:55Z","2026-12-01T22:12:20Z","2026-12-01T22:12:45Z"][i],end_utc:e.utc,target:record.target_catalog_id,attention:"TARGET_DIRECTED",gaze:"DIRECT",target_clear:true,horizon_clear:true,interruption_since_previous:false,bright_light_exposure_since_previous:false}))};
 const cases=[["valid",true,()=>{}],["wrong target",false,(r,s)=>s.looks[0].target="HIP-2"],["not searching",false,(r,s)=>s.looks[0].attention="OTHER"],["averted",false,(r,s)=>s.looks[1].gaze="AVERTED"],["zero dwell",false,(r,s)=>s.looks[0].start_utc=s.looks[0].end_utc],["cloud clearing",false,(r,s)=>s.looks[0].target_clear=false],["bright interruption",false,(r,s)=>s.looks[1].bright_light_exposure_since_previous=true],["unknown interruption",false,(r,s)=>delete s.looks[1].interruption_since_previous],["wrong original digest",false,(r,s)=>s.raw_sha256="a".repeat(64)],["missing check",false,(r,s)=>s.looks.pop()],["zero-time confirmation",false,(r,s)=>{r.checks[2].utc=r.checks[1].utc;s.looks[2].end_utc=s.looks[1].end_utc;}],["binocular",false,(r,s)=>r.checks[0].visual_aid="BINOCULAR"],["horizon blocked",false,(r,s)=>s.looks[0].horizon_clear=false],["clock linkage mismatch",false,(r,s)=>s.looks[1].end_utc="2026-12-01T22:12:24Z"],["adaptation before look too short",false,(r,s)=>r.adaptation_started_utc="2026-12-01T22:02:00Z"]];
 return cases.map(([name,expected,mut])=>{const r=JSON.parse(JSON.stringify(record)),s=JSON.parse(JSON.stringify(sidecar));mut(r,s);const a=attention(r,s);return {name,pass:a.eligible===expected&&a.model_error_seconds===null,reason:a.reason??"candidate"};});
}
export {attention,selftest};
if (typeof process!=="undefined" && process.argv.includes("--selftest")) {
 const results=selftest(); console.log(JSON.stringify(results,null,2));
 if(results.some(x=>!x.pass)) process.exitCode=1;
}

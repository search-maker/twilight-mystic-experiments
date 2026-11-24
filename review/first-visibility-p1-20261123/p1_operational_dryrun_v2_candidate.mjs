// Provisional no-sky scripted fixture only; not human observation, not admission.
// Coordinator #152 comment 7123193883. Preserve original log and custody/atmosphere/freeze gates.
function blank(){
 return {status:"DRY_RUN_ONLY_NOT_APPROVED",event_id:null,assigned_target:null,raw_sha256:null,grid_origin_utc:null,planned_slots:null,clock_error_bound_s:null,adaptation_started_utc:null,scientifically_accepted_model_sha:null,field_protocol_approved:false,looks:[]};
}

function evaluate(r){
 const fail=(reason)=>({primary_candidate:false,reason,model_error_seconds:null});
 const t=(s)=>{if(typeof s!=="string"||! /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(s))return NaN;const v=Date.parse(s);return Number.isFinite(v)&&new Date(v).toISOString()===s.replace(/(\d\d)Z$/,"$1Z").replace(/T(\d\d:\d\d:\d\d)Z$/,"T$1.000Z")?v:NaN;};
 if(!r||r.status!=="DRY_RUN_ONLY_NOT_APPROVED"||r.field_protocol_approved!==false||r.scientifically_accepted_model_sha!==null)return fail("NOT_DRY_RUN");
 if(!r.event_id||!r.assigned_target||! /^[a-f0-9]{64}$/.test(r.raw_sha256??""))return fail("MISSING_LINKAGE");
 const g=t(r.grid_origin_utc),a=t(r.adaptation_started_utc),e=r.clock_error_bound_s,n=r.planned_slots;
 if(!Number.isFinite(g)||!Number.isFinite(a)||!Number.isFinite(e)||e<0||e>5||!Number.isInteger(n)||n<3||n>216||!Array.isArray(r.looks)||r.looks.length>n)return fail("INVALID_GRID_CLOCK_OR_CAP");
 let no=null,yes=null,prev=-Infinity;
 for(let i=0;i<r.looks.length;i++){
  const l=r.looks[i];
  if(l?.slot!==i)return fail("MISSING_OR_REORDERED_SLOT");
  if(l.state==="MISSED"||l.state==="UNCERTAIN")return fail("MISSED_OR_UNCERTAIN_PRIMARY_RETAIN_RAW");
  const s=t(l.start_utc),z=t(l.end_utc),p=t(l.positive_report_utc);
  if(!Number.isFinite(s)||!Number.isFinite(z)||Math.abs(s-g-i*25000)>2000||z-s<8000||z-s>12000||s<prev||z>g+5400000||s<a+600000)return fail("INVALID_DWELL_GRID_ADAPTATION");
  if(l.target!==r.assigned_target||l.attention!=="TARGET_DIRECTED"||l.gaze!=="DIRECT"||l.visual_aid!=="NONE"||l.target_clear!==true||l.horizon_clear!==true||l.interruption_since_previous!==false||l.bright_light_exposure_since_previous!==false)return fail("INTERRUPTED_OR_INELIGIBLE_LOOK");
  if(l.state==="NO"){
   if(yes!==null||l.positive_report_utc!==null)return fail("FIRST_YES_NOT_CONFIRMED_OR_NO_WITH_POSITIVE");
   no=z;
  } else if(l.state==="YES"){
   if(yes!==null||no===null)return fail("LEFT_CENSORED_OR_REPEATED_YES");
   if(!Number.isFinite(p)||p<s||p>z||p<=no)return fail("INVALID_ACTUAL_POSITIVE_TIMESTAMP");
   yes=p;
  } else if(l.state==="CONFIRM"){
   if(yes===null||!Number.isFinite(p)||p<s||p>z||p<=yes||p-yes>60000||yes-no>60000)return fail("CONFIRMATION_INVALID");
   return {primary_candidate:true,reason:"SYNTHETIC_TIMING_ONLY",last_no_end_utc:new Date(no).toISOString(),first_yes_report_utc:new Date(yes).toISOString(),confirmation_report_utc:new Date(p).toISOString(),recorded_gap_s:(yes-no)/1000,clock_expanded_gap_s:(yes-no)/1000+2*e,primary_stop_slot:i,retained_post_confirmation_slots:r.looks.length-i-1,model_error_seconds:null};
  }else return fail("UNKNOWN_STATE");
  prev=z;
 }
 return fail("RIGHT_CENSORED_OR_UNCONFIRMED");
}

function selftest(){
 const origin=Date.parse("2030-01-01T00:00:00Z"),stamp=s=>new Date(origin+s*1000).toISOString();
 function fixture(n=4,first=1){
  const r={...blank(),event_id:"SYNTHETIC_NO_SKY",assigned_target:"SYNTHETIC_TARGET",raw_sha256:"0".repeat(64),grid_origin_utc:stamp(0),planned_slots:n,clock_error_bound_s:5,adaptation_started_utc:stamp(-610)};
  r.looks=Array.from({length:n},(_,i)=>({slot:i,state:i===first?"YES":i===first+1?"CONFIRM":"NO",start_utc:stamp(i*25),end_utc:stamp(i*25+10),positive_report_utc:i===first||i===first+1?stamp(i*25+3):null,target:r.assigned_target,attention:"TARGET_DIRECTED",gaze:"DIRECT",visual_aid:"NONE",target_clear:true,horizon_clear:true,interruption_since_previous:false,bright_light_exposure_since_previous:false}));return r;
 }
 const cases=[
 ["positive timestamp distinct from end",true,r=>{},x=>x.recorded_gap_s===18&&x.clock_expanded_gap_s===28],
 ["post-confirm interruption retained",true,r=>r.looks[3].interruption_since_previous=true,x=>x.retained_post_confirmation_slots===1],
 ["missing actual positive timestamp",false,r=>r.looks[1].positive_report_utc=null],
 ["positive outside look",false,r=>r.looks[1].positive_report_utc=stamp(36)],
 ["late start",false,r=>r.looks[1].start_utc=stamp(28)],
 ["short dwell",false,r=>r.looks[0].end_utc=stamp(7)],
 ["missed preceding slot",false,r=>r.looks[0].state="MISSED"],
 ["uncertain before YES",false,r=>r.looks[0].state="UNCERTAIN"],
 ["omitted slot",false,r=>r.looks.shift()],
 ["failed confirmation",false,r=>{r.looks[2].state="NO";r.looks[2].positive_report_utc=null;}],
 ["cloud during primary",false,r=>r.looks[1].target_clear=false],
 ["clock unknown",false,r=>r.clock_error_bound_s=null],
 ["clock beyond bound",false,r=>r.clock_error_bound_s=5.1],
 ["invalid calendar timestamp",false,r=>r.grid_origin_utc="2030-02-30T00:00:00Z"],
 ["left censor",false,r=>{r.looks[0].state="YES";r.looks[0].positive_report_utc=stamp(3);}],
 ["right censor",false,r=>r.looks.splice(2)],
 ["insufficient adaptation",false,r=>r.adaptation_started_utc=stamp(-599)],
 ["NO with positive",false,r=>r.looks[0].positive_report_utc=stamp(1)],
 ["averted",false,r=>r.looks[1].gaze="AVERTED"],
 ["not approved for real data",false,r=>r.field_protocol_approved=true],
 ["maximum cap last confirmation",true,r=>Object.assign(r,fixture(216,214)),x=>x.primary_stop_slot===215],
 ["no confirmation slot",false,r=>Object.assign(r,fixture(216,215))],
 ["over cap",false,r=>Object.assign(r,fixture(217,215))],
 ["negative clock",false,r=>r.clock_error_bound_s=-1]
 ];
 return cases.map(([name,want,mut,extra])=>{const r=fixture();mut(r);const snapshot=JSON.stringify(r);const x=evaluate(r);return {name,pass:x.primary_candidate===want&&x.model_error_seconds===null&&JSON.stringify(r)===snapshot&&(!extra||extra(x)),result:x};});
}
export {blank,evaluate,selftest};
if(typeof process!=="undefined"&&process.argv.includes("--selftest")){const r=selftest();console.log(JSON.stringify(r,null,2));if(r.some(x=>!x.pass))process.exitCode=1;}

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const HUMAN_BLOB='bb4cd0ff02159ecffe276022cec9d292c7a434a3';
const PHOT='photopicLuminanceCdM2';
const CONTRASTS=[
  ['continental_vs_native','opac-continental-average'],
  ['maritime_vs_native','opac-maritime-clean'],
  ['desert_vs_native','opac-desert'],
  ['desert_spheroids_vs_native','opac-desert-spheroids'],
];
const NATIVE='native-rural-ss';
const FIELD_FACTOR=2.4;
function die(m){throw new Error(m);}
function blobSha1(p){const b=fs.readFileSync(p);const h=Buffer.from(`blob ${b.length}\0`);return crypto.createHash('sha1').update(h).update(b).digest('hex');}
function args(argv){const o={};for(let i=2;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)die('invalid args');o[argv[i].slice(2)]=argv[i+1];}for(const k of ['truth','predictions','human-threshold','output'])if(!o[k])die(`missing --${k}`);return o;}
function finite(x){return typeof x==='number'&&Number.isFinite(x);}
function positive(x){return finite(x)&&x>0;}
function qlinear(values,q){const xs=[...values].sort((a,b)=>a-b);if(!xs.length||q<0||q>1)die('quantile input');const pos=q*(xs.length-1),lo=Math.floor(pos),hi=Math.ceil(pos);if(lo===hi)return xs[lo];const f=pos-lo;return xs[lo]*(1-f)+xs[hi]*f;}
const a=args(process.argv);const humanPath=path.resolve(a['human-threshold']);if(blobSha1(humanPath)!==HUMAN_BLOB)die('bound human threshold byte drift');const human=await import(pathToFileURL(humanPath).href);if(typeof human.limitingVMagnitude!=='function')die('limitingVMagnitude export missing');
const truth=JSON.parse(fs.readFileSync(a.truth,'utf8'));const pred=JSON.parse(fs.readFileSync(a.predictions,'utf8'));
if(truth.status!=='COMPLETE_EXACT_120_CASE_SCALAR_TRUTH'||truth.holdoutCount!==8||truth.finiteThreeReplicateStateVsNativeChannelRows!==96)die('truth identity/cardinality drift');
if(pred.status!=='PREDICTIONS_FROM_FROZEN_SELECTED_TRAINING_MODEL'||pred.geometryCount!==8||pred.selectedModelCanonicalSha256!=='0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af')die('prediction identity drift');
const pm=new Map(pred.predictions.map(r=>[String(r.geometryId),r]));const rows=[];const absErrors=[];
for(const h of truth.holdouts){const hid=String(h.holdoutId),pr=pm.get(hid);if(!pr)die(`prediction missing ${hid}`);for(const [contrast,state] of CONTRASTS){const predictedLog=pr.predictedLogContrasts?.[`${contrast}::${PHOT}`];if(!finite(predictedLog))die(`predicted photopic contrast missing ${hid} ${contrast}`);const reps=[];for(const rep of h.replicates){const n=rep.recordsByState?.[NATIVE]?.[PHOT],s=rep.recordsByState?.[state]?.[PHOT];if(!positive(n)||!positive(s))die(`nonpositive Level-B background ${hid} ${contrast}`);const ps=n*Math.exp(predictedLog);if(!positive(ps))die('predicted background nonpositive');const nlim=human.limitingVMagnitude({backgroundLuminanceCdM2:n,fieldFactor:FIELD_FACTOR,branch:'full'});const slim=human.limitingVMagnitude({backgroundLuminanceCdM2:s,fieldFactor:FIELD_FACTOR,branch:'full'});const plim=human.limitingVMagnitude({backgroundLuminanceCdM2:ps,fieldFactor:FIELD_FACTOR,branch:'full'});if(![nlim,slim,plim].every(finite))die(`nonfinite Level-B output ${hid} ${contrast}`);const direct=slim-nlim,predicted=plim-nlim,error=predicted-direct;reps.push({replicate:rep.replicate,directDeltaMag:direct,predictedDeltaMag:predicted,errorMag:error});}
const meanError=reps.reduce((z,r)=>z+r.errorMag,0)/3;const directMean=reps.reduce((z,r)=>z+r.directDeltaMag,0)/3;const predictedMean=reps.reduce((z,r)=>z+r.predictedDeltaMag,0)/3;absErrors.push(Math.abs(meanError));rows.push({holdoutId:hid,contrastId:contrast,predictedPhotopicLogContrast:predictedLog,replicates:reps,directMeanDeltaMag:directMean,predictedMeanDeltaMag:predictedMean,meanSignedDeltaErrorMag:meanError,absoluteMeanDeltaErrorMag:Math.abs(meanError)});}}
if(rows.length!==32||absErrors.length!==32)die('Level-B row count drift');const metrics={rowCount:32,meanAbsoluteDeltaErrorMag:absErrors.reduce((a,b)=>a+b,0)/32,medianAbsoluteDeltaErrorMag:qlinear(absErrors,0.5),worstAbsoluteDeltaErrorMag:Math.max(...absErrors)};const checks={meanAbsoluteDeltaErrorMag:metrics.meanAbsoluteDeltaErrorMag<=0.12,medianAbsoluteDeltaErrorMag:metrics.medianAbsoluteDeltaErrorMag<=0.10,worstAbsoluteDeltaErrorMag:metrics.worstAbsoluteDeltaErrorMag<=0.35};const out={schemaVersion:1,stageId:'asiv-v1-derived-level-b-evaluation',status:Object.values(checks).every(Boolean)?'PASS_FROZEN_LEVEL_B_GATES':'FAIL_FROZEN_LEVEL_B_GATES',fieldFactor:FIELD_FACTOR,humanThresholdGitBlobSha1:HUMAN_BLOB,humanThresholdModel:'Crumey 2014 eq.34 full branch',predictionDefinition:'apply predicted photopic ln(state/native) to each direct-MYSTIC native holdout replicate background, compute predicted state-minus-native limiting-V delta, compare with direct state-minus-native delta; score absolute error of the three-replicate mean delta per holdout/state',rows,metrics,gateChecks:checks,allLevelBGatesPass:Object.values(checks).every(Boolean),epsilonSubstitutionPerformed:false,universalClockMinuteConversionPermitted:false,levelBSeparatelyFit:false,productionAuthorized:false};fs.writeFileSync(path.resolve(a.output),`${JSON.stringify(out,null,2)}\n`,'utf8');

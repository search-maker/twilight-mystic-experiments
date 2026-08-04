#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, statistics, sys
from pathlib import Path
from typing import Any
EXPECTED_GROUPS={"g01-reference-bridge","g02-early-near-low","g03-early-perpendicular-high","g04-mid-perpendicular","g05-mid-opposite-low","g06-late-opposite-high-aerosol"}
METHODS=("reference-vroom","alis")
GEOMETRY_FIELDS=("sunDepressionDeg","targetAltitudeDeg","relativeAzimuthDeg","observerElevationM","aod550")
ALLOWED_SOURCE_STAGES={"cross-geometry-held-out-confirmation-timeout-continuation-v1","g01-fixed-precision-diagnosis-execution-v1"}
class ContractError(RuntimeError):pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ContractError(f"expected JSON object: {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def finite(v:Any,name:str)->float:
 if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)):raise ContractError(f"{name} must be finite numeric")
 return float(v)
def validate_geometry(group:str,geometry:Any)->dict[str,float]:
 if not isinstance(geometry,dict) or geometry.get("geometryId")!=group:raise ContractError(f"geometry missing/mismatched for {group}")
 result={f:finite(geometry.get(f),f"{group}.{f}") for f in GEOMETRY_FIELDS}
 if not 0<=result["sunDepressionDeg"]<=20 or not 0<=result["targetAltitudeDeg"]<=90 or not 0<=result["relativeAzimuthDeg"]<=180 or not 0<=result["observerElevationM"]<=5000 or not 0<result["aod550"]<=1:raise ContractError(f"geometry outside contract for {group}")
 return result
def validate_method(group:str,method:str,value:Any)->dict[str,Any]:
 if not isinstance(value,dict):raise ContractError(f"method statistics missing: {group} {method}")
 nodes=value.get("nodeMeanRadiance")
 if not isinstance(nodes,list) or len(nodes)!=15:raise ContractError(f"expected 15 spectral nodes: {group} {method}")
 node_values=[finite(x,f"{group}.{method}.node") for x in nodes]
 if any(x<0 for x in node_values):raise ContractError(f"negative spectral node: {group} {method}")
 values=value.get("valuesCdM2")
 if isinstance(values,list) and len(values)>=2:
  vals=[finite(x,f"{group}.{method}.value") for x in values]
  if any(x<=0 for x in vals):raise ContractError(f"nonpositive block value: {group} {method}")
  block_count=len(vals);mean=statistics.mean(vals);sd=statistics.stdev(vals);cv=sd/mean;rsem=cv/math.sqrt(block_count)
  supplied_mean=value.get("meanCdM2")
  if supplied_mean is not None and abs(finite(supplied_mean,"mean")-mean)>max(1e-15,abs(mean)*1e-12):raise ContractError(f"mean inconsistent with values: {group} {method}")
  supplied_count=value.get("blockCount")
  if supplied_count is not None and supplied_count!=block_count:raise ContractError(f"blockCount inconsistent: {group} {method}")
  supplied_rsem=value.get("relativeStandardErrorOfMean")
  if supplied_rsem is not None and abs(finite(supplied_rsem,"RSEM")-rsem)>1e-12:raise ContractError(f"RSEM inconsistent: {group} {method}")
 else:
  block_count=value.get("blockCount");mean=finite(value.get("meanCdM2"),f"{group}.{method}.mean");rsem=finite(value.get("relativeStandardErrorOfMean"),f"{group}.{method}.RSEM");vals=None
  if not isinstance(block_count,int) or block_count<2:raise ContractError(f"at least two blocks required: {group} {method}")
  if mean<=0:raise ContractError(f"nonpositive mean: {group} {method}")
  sd=value.get("sampleStandardDeviationCdM2");cv=value.get("coefficientOfVariation")
  sd=None if sd is None else finite(sd,"sd");cv=None if cv is None else finite(cv,"cv")
 if not 0<=rsem<=0.10:raise ContractError(f"RSEM exceeds anchor contract: {group} {method}: {rsem}")
 result={"blockCount":block_count,"meanCdM2":mean,"relativeStandardErrorOfMean":rsem,"nodeMeanRadiance":node_values}
 if vals is not None:result.update({"valuesCdM2":vals,"sampleStandardDeviationCdM2":sd,"coefficientOfVariation":cv})
 return result
def validate(dataset:dict[str,Any],readiness:dict[str,Any])->dict[str,Any]:
 if dataset.get("schemaVersion")!=1 or dataset.get("status")!="AUDITED_COMPUTATIONAL_REFERENCE_DATASET" or dataset.get("screeningOnly") is not True or dataset.get("observationValidationRequired") is not True:raise ContractError("dataset boundary changed")
 if dataset.get("sourceStageId") not in ALLOWED_SOURCE_STAGES:raise ContractError(f"unsupported source stage: {dataset.get('sourceStageId')}")
 required={"schemaVersion":1,"status":"COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE","computationalReferenceScreeningComplete":True,"acceptedReferenceGeometryCount":6,"heldOutConfirmationFailureCount":0,"productionModelReady":False,"observationValidationRequired":True,"surrogateTrainingAutomaticallyAuthorized":False}
 stale={k:(readiness.get(k),v) for k,v in required.items() if readiness.get(k)!=v}
 if stale or readiness.get("technicalDiagnosisRequiredGeometryIds")!=[]:raise ContractError(f"readiness boundary changed: {stale}")
 records=dataset.get("records")
 if not isinstance(records,list) or len(records)!=6:raise ContractError("reference dataset must contain exactly six geometries")
 seen=set();anchors=[]
 for record in records:
  if not isinstance(record,dict):raise ContractError("record must be object")
  group=record.get("groupId")
  if group not in EXPECTED_GROUPS or group in seen:raise ContractError(f"unexpected/duplicate group: {group}")
  seen.add(group);geometry=validate_geometry(group,record.get("geometry"));methods_raw=record.get("methodStatistics")
  if not isinstance(methods_raw,dict):raise ContractError(f"method stats missing: {group}")
  methods={m:validate_method(group,m,methods_raw.get(m)) for m in METHODS};ratio=finite(record.get("meanRatioAlisToVroom"),"ratio");fraction=finite(record.get("nodeAgreementFraction"),"fraction")
  if not 0.5<=ratio<=2.0 or fraction<0.80:raise ContractError(f"method compatibility outside contract: {group}")
  origins=record.get("methodOrigins")
  if not isinstance(origins,dict) or set(origins)!=set(METHODS):raise ContractError(f"method provenance missing: {group}")
  anchors.append({"groupId":group,"geometry":geometry,"methods":methods,"methodOrigins":origins,"meanRatioAlisToVroom":ratio,"nodeAgreementFraction":fraction,"role":"external-computational-validation-anchor","eligibleForTraining":False,"observationValidationRequired":True})
 if seen!=EXPECTED_GROUPS:raise ContractError(f"geometry universe mismatch: {sorted(EXPECTED_GROUPS-seen)}")
 anchors.sort(key=lambda x:x["groupId"])
 return {"schemaVersion":1,"stageId":"twilight-model-readiness-v1","status":"REFERENCE_ANCHORS_VALIDATED","sourceStageId":dataset["sourceStageId"],"anchorCount":6,"anchors":anchors,"trainingAutomaticallyAuthorized":False,"productionModelReady":False,"observationValidationRequired":True,"boundary":"six audited computational anchors; not a training set and not observational validation"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--dataset",type=Path,required=True);p.add_argument("--readiness",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 try:r=validate(load(a.dataset),load(a.readiness));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":"twilight-model-readiness-v1","reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())

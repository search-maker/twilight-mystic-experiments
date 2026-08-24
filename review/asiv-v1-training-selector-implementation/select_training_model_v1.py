#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path

CHANNELS=("photopicLuminanceCdM2","scotopicLuminanceScotCdM2","johnsonVEffectiveRadiance_mW_m2_nm_sr")
CONTRASTS=("continental_vs_native","maritime_vs_native","desert_vs_native","desert_spheroids_vs_native")

class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def load(p):
    v=json.loads(Path(p).read_text(encoding="utf-8")); req(isinstance(v,dict),f"object required: {p}"); return v
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
def finite(x): return math.isfinite(float(x))

def coords(cell):
    return ((float(cell["sunDepressionDeg"])-2.0)/8.5,(float(cell["targetAltitudeDeg"])-5.0)/75.0,(math.cos(math.radians(float(cell["relativeAzimuthDeg"])))+1.0)/2.0,(float(cell["aod550"])-0.05)/0.35)
def dist(a,b): return math.sqrt(sum((x-y)*(x-y) for x,y in zip(a,b)))
def qlinear(values,q):
    xs=sorted(float(x) for x in values); req(xs and 0<=q<=1,"quantile input")
    pos=q*(len(xs)-1); lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return xs[lo]
    f=pos-lo; return xs[lo]*(1-f)+xs[hi]*f

def fields(cell):
    out=[]; prim=cell.get("primary") or {}
    for contrast in CONTRASTS:
        for ch in CHANNELS:
            row=((prim.get(ch) or {}).get(contrast) or {})
            req(row.get("status")=="FINITE_THREE_REPLICATES",f"nonfinite required contrast: {cell.get('analysisCellId')} {contrast} {ch}")
            x=float(row["mean"]); req(finite(x),"nonfinite target"); out.append(x)
    req(len(out)==12,"field count"); return out

def basis4(x):
    s,a,c,o=x
    return [1.0,s,a,c,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o]

def solve(A,b):
    n=len(A); req(n==len(b) and n>0,"solve dimension")
    M=[list(map(float,A[i]))+[float(b[i])] for i in range(n)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:(abs(M[r][col]),-r)); req(abs(M[pivot][col])>1e-14,"singular matrix")
        if pivot!=col: M[col],M[pivot]=M[pivot],M[col]
        p=M[col][col]
        for j in range(col,n+1): M[col][j]/=p
        for r in range(n):
            if r==col: continue
            f=M[r][col]
            if f==0: continue
            for j in range(col,n+1): M[r][j]-=f*M[col][j]
    x=[M[i][n] for i in range(n)]; req(all(finite(v) for v in x),"nonfinite solve"); return x

def fit_ridge(train,ridge):
    X=[basis4(r["coord"]) for r in train]; d=len(X[0]); m=12
    xtx=[[0.0]*d for _ in range(d)]; xty=[[0.0]*m for _ in range(d)]
    for row,rec in zip(X,train):
        y=rec["target"]
        for i in range(d):
            for j in range(d): xtx[i][j]+=row[i]*row[j]
            for k in range(m): xty[i][k]+=row[i]*y[k]
    for i in range(1,d): xtx[i][i]+=ridge
    cols=[solve(xtx,[xty[i][k] for i in range(d)]) for k in range(m)]
    return {"coefficients":[[cols[k][i] for k in range(m)] for i in range(d)]}

def pred_ridge(model,coord):
    x=basis4(coord); C=model["coefficients"]; y=[sum(x[i]*C[i][k] for i in range(len(x))) for k in range(12)]; req(all(finite(v) for v in y),"nonfinite ridge prediction"); return y

def fit_idw(train,k,power): return {"neighbors":k,"power":power,"training":[{"cellId":r["cellId"],"coord":r["coord"],"target":r["target"]} for r in train]}
def pred_idw(model,coord):
    rows=[(dist(coord,r["coord"]),r["cellId"],r["target"]) for r in model["training"]]; rows.sort(key=lambda t:(t[0],t[1]))
    if rows[0][0]<=1e-15: return list(rows[0][2])
    use=rows[:int(model["neighbors"])]; ws=[d**(-float(model["power"])) for d,_,_ in use]; den=sum(ws)
    y=[sum(w*row[2][j] for w,row in zip(ws,use))/den for j in range(12)]; req(all(finite(v) for v in y),"nonfinite idw prediction"); return y

def candidates():
    out=[]
    for k in (4,6,8,12):
        for p in (1.0,2.0,3.0): out.append({"candidateId":f"IDW_COS_4D-k{k}-p{p:g}","family":"IDW_COS_4D","complexityRank":1,"neighbors":k,"power":p})
    for r in (1e-6,1e-4,0.01,0.1,1.0): out.append({"candidateId":f"QUADRATIC_RIDGE_COS_4D-r{r:g}","family":"QUADRATIC_RIDGE_COS_4D","complexityRank":2,"ridge":r})
    req(len(out)==17,"candidate count"); return out

def fit(spec,train): return fit_idw(train,spec["neighbors"],spec["power"]) if spec["family"]=="IDW_COS_4D" else fit_ridge(train,spec["ridge"])
def predict(spec,model,coord): return pred_idw(model,coord) if spec["family"]=="IDW_COS_4D" else pred_ridge(model,coord)

def metrics(pred_rows,truth_rows,nearest_rows,zero_rows):
    errors=[]; signed=[[] for _ in range(12)]; near_errors=[]; zero_errors=[]
    for pred,truth,near,zero in zip(pred_rows,truth_rows,nearest_rows,zero_rows):
        for j in range(12):
            e=pred[j]-truth[j]; errors.append(abs(e)); signed[j].append(e); near_errors.append(abs(near[j]-truth[j])); zero_errors.append(abs(zero[j]-truth[j]))
    mae=sum(errors)/len(errors); near_mae=sum(near_errors)/len(near_errors); zero_mae=sum(zero_errors)/len(zero_errors)
    return {"aggregateMeanAbsoluteLogContrastError":mae,"medianAbsoluteLogContrastError":qlinear(errors,0.5),"p90AbsoluteLogContrastError":qlinear(errors,0.9),"worstAbsoluteLogContrastError":max(errors),"maxOver12FieldsAbsoluteMeanSignedBias":max(abs(sum(v)/len(v)) for v in signed),"meanErrorImprovementVsNearestCellBaselineFraction":1.0-mae/near_mae if near_mae>0 else None,"meanErrorImprovementVsZeroContrastBaselineFraction":1.0-mae/zero_mae if zero_mae>0 else None,"nearestCellBaselineMae":near_mae,"zeroContrastBaselineMae":zero_mae,"allPredictionsFinite":all(finite(x) for row in pred_rows for x in row)}

def eligible(m,g):
    checks={"aggregateMeanAbsoluteLogContrastError":m["aggregateMeanAbsoluteLogContrastError"]<=float(g["aggregateMeanAbsoluteLogContrastErrorMax"]),"maxOver12FieldsAbsoluteMeanSignedBias":m["maxOver12FieldsAbsoluteMeanSignedBias"]<=float(g["maxOver12FieldsAbsoluteMeanSignedBiasMax"]),"meanErrorImprovementVsNearestCellBaselineFraction":m["meanErrorImprovementVsNearestCellBaselineFraction"] is not None and m["meanErrorImprovementVsNearestCellBaselineFraction"]>=float(g["meanErrorImprovementVsNearestCellBaselineMinFraction"]),"medianAbsoluteLogContrastError":m["medianAbsoluteLogContrastError"]<=float(g["medianAbsoluteLogContrastErrorMax"]),"p90AbsoluteLogContrastError":m["p90AbsoluteLogContrastError"]<=float(g["p90AbsoluteLogContrastErrorMax"]),"worstAbsoluteLogContrastError":m["worstAbsoluteLogContrastError"]<=float(g["worstAbsoluteLogContrastErrorMax"]),"allPredictionsFinite":m["allPredictionsFinite"] is True}
    return all(checks.values()),checks

def cv(spec,recs,gates):
    preds=[]; truths=[]; nearest=[]; zeros=[]
    for i,left in enumerate(recs):
        train=[r for j,r in enumerate(recs) if j!=i]
        try: model=fit(spec,train); pr=predict(spec,model,left["coord"])
        except (Refusal,ValueError,OverflowError,ZeroDivisionError):
            bad={"aggregateMeanAbsoluteLogContrastError":1e300,"medianAbsoluteLogContrastError":1e300,"p90AbsoluteLogContrastError":1e300,"worstAbsoluteLogContrastError":1e300,"maxOver12FieldsAbsoluteMeanSignedBias":1e300,"meanErrorImprovementVsNearestCellBaselineFraction":None,"meanErrorImprovementVsZeroContrastBaselineFraction":None,"nearestCellBaselineMae":1e300,"zeroContrastBaselineMae":1e300,"allPredictionsFinite":False}
            return bad,False,{"fitOrPrediction":False}
        nr=min(train,key=lambda r:(dist(r["coord"],left["coord"]),r["cellId"])); preds.append(pr); truths.append(left["target"]); nearest.append(nr["target"]); zeros.append([0.0]*12)
    m=metrics(preds,truths,nearest,zeros); ok,checks=eligible(m,gates); return m,ok,checks

def rank(row):
    m=row["metrics"]; return (m["aggregateMeanAbsoluteLogContrastError"],m["p90AbsoluteLogContrastError"],m["worstAbsoluteLogContrastError"],row["complexityRank"],row["candidateId"])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--protocol",required=True); ap.add_argument("--contract",required=True); ap.add_argument("--analysis-index",required=True); ap.add_argument("--report",required=True); ap.add_argument("--model",required=True); args=ap.parse_args()
    protocol=load(args.protocol); contract=load(args.contract); raw=Path(args.analysis_index).read_bytes(); analysis=json.loads(raw); bind=contract["sourceBindings"]["afpfRecoveryArtifact"]
    req(sha256_bytes(raw)==bind["analysisIndexRawSha256"],"analysis-index raw hash mismatch"); req(sha256_bytes(canonical_bytes(analysis))==bind["analysisIndexCanonicalSha256"],"analysis-index canonical hash mismatch")
    req(analysis.get("scientificOrdinal")==38 and analysis.get("analysisCellCount")==24 and len(analysis.get("cells",[]))==24,"analysis identity/cardinality drift"); req(tuple(analysis.get("primaryChannels",[]))==CHANNELS,"channel drift")
    sel=protocol["trainingOnlyInterpolatorSelection"]; gates=sel["trainingEligibilityGates"]; req(sel["crossValidation"]=="EXACT_LEAVE_ONE_AFPF_ANALYSIS_CELL_OUT_24_FOLDS","CV protocol drift"); req(sel["sameGlobalCandidateSpecRequiredForAll12Fields"] is True,"global candidate drift"); req(sel["holdoutValuesMayInfluenceSelection"] is False and sel["postHoldoutRetuningAllowed"] is False,"holdout boundary drift")
    recs=[]; seen=set()
    for cell in sorted(analysis["cells"],key=lambda c:str(c["analysisCellId"])):
        cid=str(cell["analysisCellId"]); req(cid not in seen,"duplicate cell"); seen.add(cid); recs.append({"cellId":cid,"coord":coords(cell),"target":fields(cell)})
    rows=[]
    for spec in candidates():
        m,ok,checks=cv(spec,recs,gates); rows.append({**spec,"metrics":m,"gateChecks":checks,"eligible":ok})
    good=sorted([r for r in rows if r["eligible"]],key=rank); selected=good[0] if good else None
    report={"schemaVersion":1,"stageId":"asiv-v1-training-selection","status":"ELIGIBLE_SELECTED_MODEL" if selected else "NO_ELIGIBLE_CANDIDATE_STOP_NO_ORDINAL39_AUTHORIZATION","sourceScientificOrdinal":38,"analysisIndexRawSha256":sha256_bytes(raw),"analysisIndexCanonicalSha256":sha256_bytes(canonical_bytes(analysis)),"candidateCount":len(rows),"eligibleCandidateCount":len(good),"selectedCandidateId":selected["candidateId"] if selected else None,"candidateResults":sorted(rows,key=lambda r:r["candidateId"]),"holdoutValuesOpened":False,"scientificExecutionPerformed":False,"solverExecutionPerformed":False,"ordinal39Allocated":False,"githubRerun":False,"retry":False,"resume":False}
    if selected:
        spec={k:v for k,v in selected.items() if k not in ("metrics","gateChecks","eligible")}; model=fit(spec,recs); model_out={"schemaVersion":1,"stageId":"asiv-v1-selected-training-model","status":"MATERIALIZED_FROM_ALREADY_OPENED_ORDINAL38_TRAINING_ONLY","candidateSpec":spec,"trainingCvMetrics":selected["metrics"],"trainingCvGateChecks":selected["gateChecks"],"trainingCellIds":[r["cellId"] for r in recs],"trainingCoordinates":[r["coord"] for r in recs],"model":model,"sourceAnalysisIndexRawSha256":sha256_bytes(raw),"sourceAnalysisIndexCanonicalSha256":sha256_bytes(canonical_bytes(analysis)),"holdoutValuesOpened":False,"scientificExecutionPerformed":False,"solverExecutionPerformed":False,"ordinal39Allocated":False}
    else: model_out={"schemaVersion":1,"stageId":"asiv-v1-selected-training-model","status":"NO_MODEL_MATERIALIZED_NO_ELIGIBLE_CANDIDATE","ordinal39Allocated":False,"scientificExecutionPerformed":False,"solverExecutionPerformed":False}
    report["selectedModelCanonicalSha256"]=sha256_bytes(canonical_bytes(model_out)); write(args.model,model_out); write(args.report,report)
if __name__=="__main__": main()

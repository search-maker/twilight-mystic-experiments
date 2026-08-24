#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SELECTOR=ROOT/'review/asiv-v1-training-selector-implementation/select_training_model_v1.py'
MANIFEST=HERE/'selected-model-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def git_blob(p):
    b=Path(p).read_bytes(); return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def module():
    s=importlib.util.spec_from_file_location('asiv_frozen_selector',SELECTOR); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def reconstruct(analysis_path):
    manifest=load(MANIFEST); bind=manifest['reconstructionBindings']; raw=Path(analysis_path).read_bytes(); analysis=json.loads(raw)
    if git_blob(SELECTOR)!=bind['selectorGitBlobSha1']: raise SystemExit('selector byte drift')
    if sha(raw)!=bind['analysisIndexRawSha256'] or sha(canonical(analysis))!=bind['analysisIndexCanonicalSha256']: raise SystemExit('analysis-index binding drift')
    m=module()
    if analysis.get('scientificOrdinal')!=38 or len(analysis.get('cells',[]))!=24: raise SystemExit('analysis identity/cardinality drift')
    recs=[]
    for cell in sorted(analysis['cells'],key=lambda c:str(c['analysisCellId'])):
        recs.append({'cellId':str(cell['analysisCellId']),'coord':m.coords(cell),'target':m.fields(cell)})
    ident=manifest['selectedModelIdentity']
    spec={'candidateId':ident['selectedCandidateId'],'family':ident['family'],'complexityRank':ident['complexityRank'],'neighbors':ident['neighbors'],'power':ident['power']}
    if spec!={'candidateId':'IDW_COS_4D-k8-p2','family':'IDW_COS_4D','complexityRank':1,'neighbors':8,'power':2.0}: raise SystemExit('selected candidate drift')
    model=m.fit(spec,recs)
    model_obj={'schemaVersion':1,'stageId':'asiv-v1-selected-training-model','status':'MATERIALIZED_FROM_ALREADY_OPENED_ORDINAL38_TRAINING_ONLY','candidateSpec':spec,'trainingCvMetrics':ident['trainingCvMetrics'],'trainingCvGateChecks':ident['trainingCvGateChecks'],'trainingCellIds':[r['cellId'] for r in recs],'trainingCoordinates':[r['coord'] for r in recs],'model':model,'sourceAnalysisIndexRawSha256':sha(raw),'sourceAnalysisIndexCanonicalSha256':sha(canonical(analysis)),'holdoutValuesOpened':False,'scientificExecutionPerformed':False,'solverExecutionPerformed':False,'ordinal39Allocated':False}
    got=sha(canonical(model_obj)); want=ident['selectedModelCanonicalSha256']
    if got!=want: raise SystemExit(f'selected model reconstruction hash mismatch: {got} != {want}')
    return m,spec,model,model_obj

def validate_geometry(g):
    vals={'sunDepressionDeg':(2.0,10.5),'targetAltitudeDeg':(5.0,80.0),'relativeAzimuthDeg':(0.0,180.0),'observerElevationM':(0.0,2500.0),'aod550':(0.05,0.40)}
    for k,(lo,hi) in vals.items():
        x=float(g[k])
        if not math.isfinite(x) or x<lo or x>hi: raise SystemExit(f'geometry outside frozen operational box: {k}={x}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--analysis-index',required=True); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); args=ap.parse_args()
    m,spec,model,model_obj=reconstruct(args.analysis_index); inp=load(args.input); geoms=inp.get('geometries')
    if not isinstance(geoms,list) or not geoms: raise SystemExit('input.geometries nonempty list required')
    field_names=[f'{contrast}::{channel}' for contrast in m.CONTRASTS for channel in m.CHANNELS]
    out=[]
    train=model['training']
    for row in geoms:
        gid=str(row.get('geometryId') or ''); g=row.get('geometry') if isinstance(row.get('geometry'),dict) else row
        validate_geometry(g); c=m.coords(g); y=m.predict(spec,model,c)
        nearest=min((m.dist(c,r['coord']),r['cellId']) for r in train)
        out.append({'geometryId':gid,'geometry':{k:float(g[k]) for k in ('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')},'observerElevationUsedByInterpolator':False,'nearestOrdinal38TrainingCellId':nearest[1],'nearestOrdinal38TrainingDistance4D':nearest[0],'predictedLogContrasts':dict(zip(field_names,y))})
    value={'schemaVersion':1,'stageId':'asiv-v1-selected-model-evaluation','status':'PREDICTIONS_FROM_FROZEN_SELECTED_TRAINING_MODEL','selectedCandidateId':spec['candidateId'],'selectedModelCanonicalSha256':sha(canonical(model_obj)),'geometryCount':len(out),'predictions':out,'scientificExecutionPerformed':False,'solverExecutionPerformed':False,'ordinal39Allocated':False,'freshHoldoutTruthOpenedByEvaluator':False}
    Path(args.output).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__': main()

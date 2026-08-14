#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, math, re, subprocess, zipfile
from pathlib import Path
from typing import Any

BASE_ANALYZER='review/core-training-spectral-representation-v2/analyze_v2.py'
BASE_PROTOCOL='review/core-training-spectral-representation-v2/protocol-v2.json'
BASE_ANALYZER_BLOB='a82188dab1377c1af33ce0c4c23fa0a382f2978f'
BASE_PROTOCOL_BLOB='678dc545436e1d8d77504b165d011f68b0040d8c'
FEATURES=('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
TOLERANCE={
    'sunDepressionDeg':1.0e-6,
    'targetAltitudeDeg':1.0e-5,
    'relativeAzimuthDeg':1.0e-6,
    'observerElevationM':5.1e-4,
    'aod550':5.1e-7,
}
GID_RE=re.compile(r'(?<![A-Za-z0-9])train-[0-9]{4}(?![A-Za-z0-9])')

class Refusal(RuntimeError): pass

def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)

def load_json(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8'))
    req(isinstance(x,dict),f'object required: {p}')
    return x

def git_blob(root:Path,path:str)->str:
    return subprocess.check_output(['git','rev-parse',f'HEAD:{path}'],cwd=root,text=True).strip()

def validate_protocol(p:dict[str,Any])->None:
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(
        1,
        'level-b-v1-core-training-spectral-representation-v2-source-binding-fix-v1',
        'REVIEW_ONLY_MECHANICAL_SOURCE_BINDING_CORRECTION_NO_NEW_SCIENCE_NO_HOLDOUT_NO_FITTING',
        'MYSTIC-STATE-0067'),'correction protocol identity drift')
    req(p.get('sourceMainAtFreeze')=='a2621bba6ffc7ac477387995dce953cffb2782cb','source main drift')
    b=p.get('baseRepresentation') or {}
    req((b.get('protocolPath'),b.get('protocolGitBlobSha'),b.get('analyzerPath'),b.get('analyzerGitBlobSha'))==(
        BASE_PROTOCOL,BASE_PROTOCOL_BLOB,BASE_ANALYZER,BASE_ANALYZER_BLOB),'base representation binding drift')
    f=p.get('failedExecution') or {}
    req((f.get('activationCommitSha'),f.get('activationParentMainSha'),f.get('runId'),f.get('runAttempt'),f.get('event'),f.get('conclusion'))==(
        'a2a860f54485d2dc33a6f448a2b9e4fd01fe652e','a2621bba6ffc7ac477387995dce953cffb2782cb',31770243803,1,'push','failure'),'failed execution identity drift')
    req(f.get('exactRefusalReason')=='prepared geometry inputs missing','failed execution refusal drift')
    req(f.get('protectedHoldoutValuesRead') is False and f.get('scientificSolverExecutionPerformed') is False and f.get('outputArtifactCreated') is False,'failed execution boundary drift')
    c=p.get('correction') or {}
    req(c.get('geometryFeatureSource')=='EXACT_ARCHIVED_INPUT_RESOLVED_TXT_RENDERED_SOLVER_DIRECTIVES','geometry source drift')
    req(c.get('geometryIdRule')=='UNIQUE_TRAIN_4DIGIT_ID_AGREED_BY_PREPARED_ID_FIELDS_OR_CASE_ID_AND_MC_BASENAME','geometry id rule drift')
    req(c.get('richPreparedCrossCheckRequiredWhenAvailable') is True,'prepared cross-check drift')
    req(c.get('inputResolvedSha256CrossCheckRequired') is True,'input hash cross-check drift')
    expected={
        'sunDepressionDeg':'sza - 90.0',
        'targetAltitudeDeg':'degrees(asin(-umu))',
        'relativeAzimuthDeg':'phi with phi0 required exactly 0',
        'observerElevationM':'1000 * first atm_z_grid node with zout required exactly 0',
        'aod550':'unique aerosol_set_tau_at_wvl 550 value',
    }
    req(c.get('featureTransforms')==expected,'feature transform drift')
    req(c.get('serializationTolerance')==TOLERANCE,'serialization tolerance drift')
    for k in ('scientificCriterionChanged','pcaRuleChanged','snrThresholdChanged','trainingUniverseChanged','rawSpectrumTransformationAdded'):
        req(c.get(k) is False,f'forbidden science change opened: {k}')
    bounds=p.get('boundaries') or {}
    for k in ('scientificSolverExecutionAuthorized','newScientificOrdinalAuthorized','protectedHoldoutOpeningAuthorized','holdoutValuesMayBeRead','stage2Authorized','modelFittingAuthorized','modelSelectionAuthorized','oodFreezeAuthorizedByThisProtocol','definitionOfDoneFreezeAuthorizedByThisProtocol','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(bounds.get(k) is False,f'closed boundary opened: {k}')

def _one_directive(rows:list[list[str]],name:str)->list[str]:
    hits=[r[1:] for r in rows if r and r[0]==name]
    req(len(hits)==1,f'{name} directive count drift: {len(hits)}')
    return hits[0]

def _float_token(xs:list[str],name:str)->float:
    req(len(xs)==1,f'{name} token count drift')
    try: v=float(xs[0])
    except Exception as e: raise Refusal(f'{name} non-numeric') from e
    req(math.isfinite(v),f'{name} non-finite')
    return v

def _extract_gid(texts:list[str])->str:
    ids=[]
    for t in texts:
        ids.extend(GID_RE.findall(t))
    unique=sorted(set(ids))
    req(len(unique)==1,f'geometry id ambiguity: {unique}')
    return unique[0]

def prepared_inputs(raw:bytes)->dict[str,Any]:
    prepared=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        input_names=[n for n in z.namelist() if Path(n).name=='input-resolved.txt']
        req(len(input_names)==1,f'input-resolved member count drift: {len(input_names)}')
        input_bytes=z.read(input_names[0])
        try: input_text=input_bytes.decode('utf-8')
        except Exception as e: raise Refusal('input-resolved is not utf-8') from e
        for n in z.namelist():
            if not n.lower().endswith('.json') or 'prepared' not in Path(n).name.lower(): continue
            try: x=json.loads(z.read(n))
            except Exception: continue
            if isinstance(x,dict): prepared.append(x)
    req(prepared,'prepared binding metadata missing')
    input_sha=hashlib.sha256(input_bytes).hexdigest()
    bound_hashes=[str(x.get('inputResolvedSha256')) for x in prepared if x.get('inputResolvedSha256')]
    req(bound_hashes and set(bound_hashes)=={input_sha},'prepared/input-resolved hash binding drift')

    id_texts=[]
    for x in prepared:
        for obj in (x, x.get('inputs') if isinstance(x.get('inputs'),dict) else None):
            if not isinstance(obj,dict): continue
            for k in ('geometryId','groupId','caseId'):
                if isinstance(obj.get(k),str): id_texts.append(obj[k])
    rows=[]
    for line in input_text.splitlines():
        s=line.strip()
        if not s or s.startswith('#'): continue
        rows.append(s.split())
    mcbase=' '.join(_one_directive(rows,'mc_basename'))
    gid=_extract_gid(id_texts+[mcbase])

    sza=_float_token(_one_directive(rows,'sza'),'sza')
    phi0=_float_token(_one_directive(rows,'phi0'),'phi0')
    phi=_float_token(_one_directive(rows,'phi'),'phi')
    umu=_float_token(_one_directive(rows,'umu'),'umu')
    zout=_float_token(_one_directive(rows,'zout'),'zout')
    atm=_one_directive(rows,'atm_z_grid')
    req(atm,'atm_z_grid empty')
    try: atm0=float(atm[0])
    except Exception as e: raise Refusal('atm_z_grid first node non-numeric') from e
    req(math.isfinite(atm0),'atm_z_grid first node non-finite')
    tau=[]
    for r in rows:
        if not r or r[0]!='aerosol_set_tau_at_wvl': continue
        req(len(r)==3,'aerosol_set_tau_at_wvl token count drift')
        try: w=float(r[1]); v=float(r[2])
        except Exception as e: raise Refusal('aerosol_set_tau_at_wvl non-numeric') from e
        if w==550.0: tau.append(v)
    req(len(tau)==1,f'aod550 directive count drift: {len(tau)}')
    req(phi0==0.0,'phi0 must be exactly zero for relative-azimuth binding')
    req(zout==0.0,'zout must be exactly zero for site-altitude binding')
    req(-1.0<=umu<=1.0,'umu outside [-1,1]')
    geom={
        'sunDepressionDeg':sza-90.0,
        'targetAltitudeDeg':math.degrees(math.asin(-umu)),
        'relativeAzimuthDeg':phi,
        'observerElevationM':1000.0*atm0,
        'aod550':tau[0],
    }
    req(all(math.isfinite(v) for v in geom.values()),'non-finite geometry feature')

    rich=[]
    for x in prepared:
        y=x.get('inputs') if isinstance(x.get('inputs'),dict) else x
        if all(k in y for k in FEATURES): rich.append(y)
    for y in rich:
        for k in FEATURES:
            try: expected=float(y[k])
            except Exception as e: raise Refusal(f'rich prepared {k} non-numeric') from e
            req(math.isfinite(expected),f'rich prepared {k} non-finite')
            req(abs(geom[k]-expected)<=TOLERANCE[k],f'input-resolved/rich prepared mismatch: {k}: {geom[k]} vs {expected}')
    return {'geometryId':gid,'geometry':geom}

def load_base(root:Path):
    p=root/BASE_ANALYZER
    s=importlib.util.spec_from_file_location('spectral_representation_v2_base',p)
    req(s is not None and s.loader is not None,'base analyzer load')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m

def execute(root:Path,correction_protocol:Path,out:Path)->None:
    p=load_json(correction_protocol); validate_protocol(p)
    req(git_blob(root,BASE_PROTOCOL)==BASE_PROTOCOL_BLOB,'base protocol git blob drift')
    req(git_blob(root,BASE_ANALYZER)==BASE_ANALYZER_BLOB,'base analyzer git blob drift')
    base=load_base(root)
    base.prepared_inputs=prepared_inputs
    base.execute(root,root/BASE_PROTOCOL,out)

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('validate'); v.add_argument('--protocol',type=Path,required=True)
    e=sub.add_parser('execute'); e.add_argument('--repo-root',type=Path,required=True); e.add_argument('--protocol',type=Path,required=True); e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.cmd=='validate': validate_protocol(load_json(a.protocol))
        else: execute(a.repo_root,a.protocol,a.output)
        return 0
    except Exception as x:
        print(json.dumps({'status':'REFUSED','reason':str(x)},sort_keys=True),file=__import__('sys').stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())

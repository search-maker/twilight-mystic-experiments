#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, re
from pathlib import Path
from typing import Any
KM_PHOT=683.002; KM_SCOT=1700.06
CIE_WL=tuple(float(w) for w in range(380,781,10))
V_PHOT=(0.00004,0.00012,0.0004,0.0012,0.0040,0.0116,0.023,0.038,0.060,0.09098,0.13902,0.20802,0.323,0.503,0.710,0.862,0.954,0.99495,0.995,0.952,0.870,0.757,0.631,0.503,0.381,0.265,0.175,0.107,0.061,0.032,0.017,0.00821,0.004102,0.002091,0.001047,0.00052,0.000249,0.00012,0.00006,0.00003,0.000015)
V_SCOT=(0.000589,0.002209,0.00929,0.03484,0.0966,0.1998,0.3281,0.455,0.567,0.676,0.793,0.904,0.982,0.997,0.935,0.811,0.650,0.481,0.3288,0.2076,0.1212,0.0655,0.03315,0.01593,0.00737,0.003335,0.001497,0.000677,0.0003129,0.000148,0.0000715,0.00003533,0.0000178,0.00000914,0.00000478,0.000002546,0.000001379,0.00000076,0.000000425,0.000000241,0.000000139)
BESSELL=((470.,0.),(480.,.03),(490.,.163),(500.,.458),(510.,.78),(520.,.967),(530.,1.),(540.,.973),(550.,.898),(560.,.792),(570.,.684),(580.,.574),(590.,.461),(600.,.359),(610.,.27),(620.,.197),(630.,.135),(640.,.081),(650.,.045),(660.,.025),(670.,.017),(680.,.013),(690.,.009),(700.,0.))
RUNTIME_KEYS=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_path(p:Path)->str: return sha_bytes(p.read_bytes())
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def write_json(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def interp(tab:tuple[float,...],w:float)->float:
    if w<CIE_WL[0] or w>CIE_WL[-1]: return 0.0
    if w==CIE_WL[-1]: return tab[-1]
    x=(w-380.)/10.; i=int(math.floor(x)); f=x-i; return tab[i]*(1-f)+tab[i+1]*f
def bess(w:float)->float:
    if w<470 or w>700: return 0.0
    if w==700: return 0.0
    x=(w-470.)/10.; i=int(math.floor(x)); f=x-i; return BESSELL[i][1]*(1-f)+BESSELL[i+1][1]*f
def trap(wl:list[float],r:list[float],weight,km:float)->float:
    return km*1e-3*sum(.5*(weight(wl[i])*r[i]+weight(wl[i+1])*r[i+1])*(wl[i+1]-wl[i]) for i in range(len(wl)-1))
def johnson(wl:list[float],r:list[float])->float:
    num=den=0.0
    for i in range(len(wl)-1):
        dl=wl[i+1]-wl[i]; a=bess(wl[i])*wl[i]; b=bess(wl[i+1])*wl[i+1]; num+=.5*(a*r[i]+b*r[i+1])*dl; den+=.5*(a+b)*dl
    req(den>0,'Johnson V zero support'); return num/den
def channels(wl:list[float],r:list[float])->dict[str,float]:
    return {'photopicLuminanceCdM2':trap(wl,r,lambda w:interp(V_PHOT,w),KM_PHOT),'scotopicLuminanceScotCdM2':trap(wl,r,lambda w:interp(V_SCOT,w),KM_SCOT),'johnsonVEffectiveRadiance_mW_m2_nm_sr':johnson(wl,r)}

def parse_spectrum_bytes(data:bytes,grid_contract:dict[str,Any])->dict[str,Any]:
    text=data.decode('utf-8',errors='strict'); rows=[]; tokens=[]; wl=[]; last=[]; all_values=[]
    token_re=re.compile(grid_contract['tokenRegex'])
    for line in text.splitlines():
        p=line.split()
        if not p: continue
        req(len(p)>=2,'raw spectrum row has too few columns')
        req(token_re.fullmatch(p[0]) is not None,'wavelength token serialization drift')
        try: vals=[float(x) for x in p]
        except ValueError as e: raise Refusal('non-numeric raw spectrum token') from e
        req(all(math.isfinite(v) for v in vals),'nonfinite raw spectrum token')
        req(all(v>=0.0 for v in vals[1:]),'negative raw spectrum value')
        rows.append(p); tokens.append(p[0]); wl.append(vals[0]); last.append(vals[-1]); all_values.extend(vals[1:])
    req(len(tokens)==grid_contract['nodeCount'],'raw spectrum node count drift')
    req(tokens[0]==grid_contract['firstToken'] and tokens[-1]==grid_contract['lastToken'],'raw spectrum endpoint token drift')
    req(all(wl[i+1]>wl[i] for i in range(len(wl)-1)),'raw spectrum order drift')
    stream=('\n'.join(tokens)+'\n').encode('utf-8')
    gsha=sha_bytes(stream); req(gsha==grid_contract['canonicalTokenStreamSha256'],f'raw wavelength token grid drift: {gsha}')
    legacy_ok=all(abs((wl[i+1]-wl[i])-float(grid_contract['legacyExpectedStepNm']))<float(grid_contract['legacyStepToleranceNm']) for i in range(len(wl)-1))
    if grid_contract.get('legacyRefusalMustReproduce'):
        req(not legacy_ok,'legacy step parser unexpectedly accepts emitted grid')
    return {'wavelengthTokens':tokens,'wavelengths':wl,'lastColumn':last,'allValues':all_values,'gridSha256':gsha,'legacyParserAccepts':legacy_ok,'rowCount':len(tokens),'columnCounts':sorted(set(len(r) for r in rows)),'exactZeroScalarCount':sum(v==0.0 for v in all_values),'rawAllZeroLastColumn':all(v==0.0 for v in last)}

def validate_contract(contract:dict[str,Any])->None:
    req(contract.get('contractId')=='tier2-stage1-ordinal20-artifact-salvage-v1','contract id drift')
    req(contract.get('status')=='FROZEN_ARTIFACT_ONLY_RECOVERY_NO_SOLVER_NO_HOLDOUT','contract status drift')
    b=contract.get('boundaries') or {}
    req(b.get('trainingOnly') is True and b.get('sourceArtifactsImmutable') is True,'artifact/training boundary drift')
    for k in ('protectedHoldoutOpeningAuthorized','stage2Authorized','modelFittingAuthorized','modelSelectionAuthorized','newSolverExecutionAuthorized','githubRerunAuthorized','retryAuthorized','resumeAuthorized'):
        req(b.get(k) is False,f'closed boundary opened: {k}')
    g=contract.get('gridSerialization') or {}
    req(g.get('nodeCount')==8001 and g.get('firstToken')=='380.00000' and g.get('lastToken')=='780.00000','grid contract drift')
    req(g.get('canonicalTokenStreamSha256')=='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477','grid hash drift')
    for k in ('resamplingAllowed','smoothingAllowed','epsilonSubstitutionAllowed','rawRadianceEditingAllowed'):
        req(g.get(k) is False,f'forbidden raw operation enabled: {k}')

def validate_manifest(manifest:dict[str,Any])->None:
    req(manifest.get('caseCount')==76 and manifest.get('geometryCount')==19 and manifest.get('trainingOnly') is True,'stage1 manifest accounting drift')
    req(manifest.get('configuredPhotonHistories')==2_120_000_000,'stage1 photon accounting drift')
    req(all(c.get('role')=='surrogate-training' and c.get('executionStage')=='TRAINING_ACQUISITION' for c in manifest.get('cases',[])),'non-training case in stage1 manifest')
    req((manifest.get('closedBoundaries') or {}).get('protectedHoldoutOpeningAuthorized') is False,'manifest holdout boundary opened')

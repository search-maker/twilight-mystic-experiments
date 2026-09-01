#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, shutil, sys, time
from pathlib import Path
import numpy as np

STAGE='koomen-support-estimator-pilot-v1'
EXECUTION_KEY='koomen-support-estimator-pilot-v1:scientific:51'
ROWS=[18,22,27]
BASES=[1551000000,1552000000,1553000000,1554000000,1555000000,1556000000]
PHOTONS=200000
DIRECTIONS=[
 {'directionIndex':0,'thetaDeg':0.0,'relativeAzimuthDeg':0.0,'label':'center'},
 {'directionIndex':1,'thetaDeg':0.75,'relativeAzimuthDeg':0.0,'label':'edge_0'},
 {'directionIndex':2,'thetaDeg':0.75,'relativeAzimuthDeg':90.0,'label':'edge_90'},
 {'directionIndex':3,'thetaDeg':0.75,'relativeAzimuthDeg':180.0,'label':'edge_180'},
 {'directionIndex':4,'thetaDeg':0.75,'relativeAzimuthDeg':270.0,'label':'edge_270'},
]
METHODS=['off','on']
CAMS_PROFILE_SHA='6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359'
CIE_WL=np.arange(380.0,781.0,10.0)
V_PHOT=np.array([0.00004,0.00012,0.0004,0.0012,0.0040,0.0116,0.023,0.038,0.060,0.09098,0.13902,0.20802,0.323,0.503,0.710,0.862,0.954,0.99495,0.995,0.952,0.870,0.757,0.631,0.503,0.381,0.265,0.175,0.107,0.061,0.032,0.017,0.00821,0.004102,0.002091,0.001047,0.00052,0.000249,0.00012,0.00006,0.00003,0.000015],float)
KM_PHOTOPIC=683.002
class Failure(RuntimeError): pass

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def load_module(path,name):
 s=importlib.util.spec_from_file_location(name,path)
 if s is None or s.loader is None: raise Failure(f'cannot import {path}')
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def load_manifest(path):
 m=json.loads(path.read_text())
 assert m['stageId']==STAGE and m['executionKey']==EXECUTION_KEY
 assert m['rows']==ROWS and m['replicateSeedBases']==BASES
 assert m['photonsPerDirectionPerCaseMethod']==PHOTONS
 assert m['methods']==['mc_vroom_off','mc_vroom_on']
 assert m['fixedDirections']==DIRECTIONS
 assert m['profileSha256']==CAMS_PROFILE_SHA
 return m

def mutate_estimator(text,method):
 if text.count('mc_vroom off')!=1: raise Failure('expected exactly one mc_vroom off in source render')
 text=text.replace('mc_vroom off',f'mc_vroom {method}')
 if 'mc_escape ' in text: raise Failure('unexpected pre-existing explicit mc_escape')
 text=text.replace('mc_vroom '+method,'mc_vroom '+method+'\nmc_escape on')
 return text

def photopic(wl,L):
 r=np.interp(wl,CIE_WL,V_PHOT,left=0.0,right=0.0)
 q=KM_PHOTOPIC*float(np.trapezoid(L*r,wl))
 if not q>0 or not math.isfinite(q): raise Failure('invalid photopic q')
 return q

def execute(base,uvspec,text,case_dir,theta,tables):
 case_dir.mkdir(parents=True,exist_ok=False); (case_dir/'input-resolved.txt').write_text(text)
 t=time.monotonic(); syntax=base.run_process(uvspec,text,case_dir,syntax=True); solver=base.run_process(uvspec,text,case_dir,syntax=False); wall=time.monotonic()-t
 rad=case_dir/'mc.rad.spc'; std=case_dir/'mc.rad.std.spc'
 if not rad.is_file() or not std.is_file(): raise Failure('missing spectra')
 wl,L=base.parse_spectrum(rad); qcie=photopic(wl,L); qsqm,qstd,n,w0,w1=base.integrate_ray(rad,std,theta,tables)
 if not qsqm>0 or not math.isfinite(qsqm): raise Failure('invalid sqm q')
 rec={'ciePhotopicQ':qcie,'sqmConditionalQ':qsqm,'sqmStdDiagnosticNotBetweenSeed':qstd,'syntaxSeconds':syntax,'solverSeconds':solver,'wallSeconds':wall,'spectrumRows':n,'wavelengthStartNm':w0,'wavelengthEndNm':w1,'inputSha256':hashlib.sha256(text.encode()).hexdigest(),'radianceSha256':sha(rad),'stdSha256':sha(std)}
 shutil.rmtree(case_dir,ignore_errors=True); return rec

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--replicate',type=int,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--profile-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--cams-profile',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
 a=ap.parse_args(); load_manifest(a.manifest)
 if a.row not in ROWS or not 1<=a.replicate<=6: raise Failure('row/replicate outside frozen pilot')
 base=load_module(a.baseline_runner,'baseline'); prof=load_module(a.profile_runner,'profile')
 obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); profiles,sanity=prof.load_cams_profile(a.cams_profile)
 if sha(a.cams_profile)!=CAMS_PROFILE_SHA: raise Failure('profile sha changed')
 out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False); data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); uv=a.uvspec.resolve()
 tau=out/'cams-site-grid-tau.dat'; meta=prof.write_tau_profile(base,atm,profiles,prof.parse_utc(obs['utc']),tau)
 aod=float(obs['aod550_primary_frozen']); seed=BASES[a.replicate-1]+a.row*1000+960
 result={}
 for method in METHODS:
  result[method]={}
  for case in ['baseline','profile']:
   arr=[]
   for d in DIRECTIONS:
    ray={'thetaDeg':d['thetaDeg'],'relativeAzimuthDeg':d['relativeAzimuthDeg']}
    cdir=out/'work'/method/case/d['label']
    text=base.render(data,atm,cdir,obs,ray,aod,PHOTONS,seed) if case=='baseline' else prof.render_profile(base,data,atm,cdir,obs,ray,aod,seed,tau)
    text=mutate_estimator(text,method)
    arr.append({**d,**execute(base,uv,text,cdir,d['thetaDeg'],tables)})
   result[method][case]=arr
 payload={'schemaVersion':1,'stageId':STAGE,'executionKey':EXECUTION_KEY,'status':'COMPLETED','row':a.row,'replicate':a.replicate,'seedBase':BASES[a.replicate-1],'seed':seed,'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'comparisonRole':obs['comparison_role'],'aod550FrozenIdentical':aod,'photonsPerDirectionPerCaseMethod':PHOTONS,'methods':{'off':'mc_vroom off + mc_escape on','on':'mc_vroom on + mc_escape on'},'directions':DIRECTIONS,'profileSanity':sanity,'profileTauMeta':meta,'results':result,'TaylorResidualUsed':False,'productionAuthorized':False}
 (out/'pilot-result.json').write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':'COMPLETED','row':a.row,'replicate':a.replicate,'solverCalls':20},sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception as e:
  print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(e)}),file=sys.stderr); raise

#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from typing import Any
class Refusal(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(v:bytes)->str: return hashlib.sha256(v).hexdigest()
def sha_file(p:Path)->str: return sha_bytes(p.read_bytes())
def git_blob_sha1(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text()); require(isinstance(v,dict),f'expected object: {p}'); return v
def verify_self(v:dict[str,Any],field:str)->None:
    supplied=v.get(field); require(isinstance(supplied,str) and len(supplied)==64,f'{field} missing')
    bare={k:x for k,x in v.items() if k!=field}; require(canon(bare)==supplied,f'{field} self-hash mismatch')
def sample_stats(values:list[float])->dict[str,float]:
    require(len(values)==4,'exactly four values required'); require(all(isinstance(x,(int,float)) and math.isfinite(float(x)) for x in values),'nonfinite value')
    vals=[float(x) for x in values]; mean=sum(vals)/4.0; require(mean>0.0,'nonpositive mean')
    var=sum((x-mean)**2 for x in vals)/3.0; sd=math.sqrt(var); return {'mean':mean,'sampleStd':sd,'rsem':sd/2.0/mean}
PRIMARY=['photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr']

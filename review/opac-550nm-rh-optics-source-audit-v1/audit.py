from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_ARCHIVE_MEMBERS = 28
ASSETS = {
    "INSO": ("data/aerosol/OPAC/optprop/inso.mie.cdf", "fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407"),
    "WASO": ("data/aerosol/OPAC/optprop/waso.mie.cdf", "b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5"),
    "SOOT": ("data/aerosol/OPAC/optprop/soot.mie.cdf", "44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02"),
    "SUSO": ("data/aerosol/OPAC/optprop/suso.mie.cdf", "ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472"),
}


class AuditError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def extract_exact_assets(archive: Path, outdir: Path) -> dict[str, Any]:
    if archive.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise AuditError(f"archive size drift: {archive.stat().st_size}")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise AuditError("archive SHA drift")
    wanted={rel:(species,want_sha) for species,(rel,want_sha) in ASSETS.items()}
    found={}
    with tarfile.open(archive,'r:gz') as tf:
        members=tf.getmembers()
        if len(members)!=EXPECTED_ARCHIVE_MEMBERS:
            raise AuditError(f"archive member-count drift: {len(members)}")
        for m in members:
            pp=PurePosixPath(m.name)
            if pp.is_absolute() or '..' in pp.parts:
                raise AuditError(f"unsafe archive member: {m.name}")
            if m.name not in wanted:
                continue
            if not m.isfile():
                raise AuditError(f"wanted asset is not regular file: {m.name}")
            src=tf.extractfile(m)
            if src is None:
                raise AuditError(f"cannot stream asset: {m.name}")
            data=src.read()
            species,want_sha=wanted[m.name]
            got=sha256_bytes(data)
            if got!=want_sha:
                raise AuditError(f"asset SHA drift: {species}: {got}")
            dest=outdir/f"{species}.cdf"
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
            found[species]={"archiveMember":m.name,"sha256":got,"byteCount":len(data),"localFile":dest.name}
    if set(found)!=set(ASSETS):
        raise AuditError(f"missing assets: {sorted(set(ASSETS)-set(found))}")
    return found


def _jsonable(value: Any) -> Any:
    if isinstance(value,(str,int,bool)) or value is None:
        return value
    if isinstance(value,float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value,bytes):
        return value.decode('utf-8','replace')
    if hasattr(value,'tolist'):
        return _jsonable(value.tolist())
    if isinstance(value,(list,tuple)):
        return [_jsonable(x) for x in value]
    if isinstance(value,dict):
        return {str(k):_jsonable(v) for k,v in value.items()}
    return str(value)


def _attrs(obj: Any) -> dict[str,Any]:
    out={}
    for k in getattr(obj,'ncattrs',lambda:[])():
        try: out[k]=_jsonable(obj.getncattr(k))
        except Exception as exc: out[k]=f"<unreadable:{type(exc).__name__}>"
    return out


def _candidate_score(name: str, attrs: dict[str,Any], kind: str) -> bool:
    blob=(name+' '+json.dumps(attrs,sort_keys=True)).lower()
    if kind=='wavelength': return bool(re.search(r'wav|wvl|lambda|wavelength',blob))
    if kind=='humidity': return bool(re.search(r'humid|relative humidity|\brh\b|r\.h\.',blob))
    if kind=='extinction': return bool(re.search(r'extinction|ext\b|extcoef|ext_coeff|mass extinction',blob))
    return False


def inspect_netcdf(path: Path) -> dict[str,Any]:
    import numpy as np
    from netCDF4 import Dataset
    out={"file":path.name,"sha256":sha256_file(path),"byteCount":path.stat().st_size}
    with Dataset(path,'r') as ds:
        out["dataModel"]=ds.data_model
        out["globalAttributes"]=_attrs(ds)
        out["dimensions"]={name:{"size":len(dim),"unlimited":bool(dim.isunlimited())} for name,dim in ds.dimensions.items()}
        vars_meta={}
        candidates={"wavelength":[],"humidity":[],"extinction":[]}
        for name,var in ds.variables.items():
            attrs=_attrs(var)
            meta={"dimensions":list(var.dimensions),"shape":list(var.shape),"dtype":str(var.dtype),"attributes":attrs}
            size=1
            for n in var.shape: size*=int(n)
            if var.ndim==1 and size<=10000:
                try:
                    arr=np.ma.asarray(var[:])
                    vals=arr.compressed() if np.ma.isMaskedArray(arr) else np.asarray(arr).reshape(-1)
                    meta["values"]=_jsonable(vals)
                    if vals.size and np.issubdtype(vals.dtype,np.number):
                        finite=np.asarray(vals,dtype=float); finite=finite[np.isfinite(finite)]
                        if finite.size: meta["numericMinMax"]=[float(finite.min()),float(finite.max())]
                except Exception as exc:
                    meta["valuesError"]=f"{type(exc).__name__}: {exc}"
            vars_meta[name]=meta
            for kind in candidates:
                if _candidate_score(name,attrs,kind): candidates[kind].append(name)
        out["variables"]=vars_meta
        out["candidateVariables"]=candidates

        # Freeze compact candidate slices only; do not dump huge phase matrices.
        extracts=[]
        wavelength_names=candidates['wavelength']
        humidity_names=candidates['humidity']
        extinction_names=candidates['extinction']
        for ename in extinction_names:
            var=ds.variables[ename]
            if var.ndim>4:
                continue
            rec={"variable":ename,"dimensions":list(var.dimensions),"shape":list(var.shape),"attributes":_attrs(var)}
            # For each associated 1-D coordinate, report nearest 550 nm and all compact RH values.
            coord_info={}
            for dim in var.dimensions:
                if dim not in ds.variables or ds.variables[dim].ndim!=1: continue
                cv=ds.variables[dim]
                try: vals=np.asarray(cv[:],dtype=float).reshape(-1)
                except Exception: continue
                info={"attributes":_attrs(cv),"values":_jsonable(vals) if vals.size<=100 else None}
                text=(dim+' '+json.dumps(info['attributes'])).lower()
                if re.search(r'wav|wvl|lambda|wavelength',text) and vals.size:
                    # Determine numeric coordinate nearest 550 or 0.55, based on scale.
                    target=0.55 if np.nanmax(np.abs(vals))<100 else 550.0
                    idx=int(np.nanargmin(np.abs(vals-target)))
                    info["nearest550"]={"index":idx,"coordinateValue":float(vals[idx]),"targetNumeric":target}
                coord_info[dim]=info
            rec["coordinates"]=coord_info
            extracts.append(rec)
        out["extinctionCandidateStructure"]=extracts
    return out


def parse_afgl(path: Path) -> dict[str,Any]:
    raw=path.read_bytes(); text=raw.decode('utf-8')
    comments=[]; rows=[]
    for n,line in enumerate(text.splitlines(),1):
        s=line.strip()
        if not s: continue
        if s.startswith('#'): comments.append({"line":n,"text":line}); continue
        vals=s.split()
        try: nums=[float(x) for x in vals]
        except ValueError as exc: raise AuditError(f"AFGL nonnumeric row {n}: {line}") from exc
        rows.append({"line":n,"values":nums})
    return {"sha256":sha256_bytes(raw),"byteCount":len(raw),"lineCount":len(text.splitlines()),"commentLines":comments,"numericRows":rows,"numericColumnCounts":sorted({len(r['values']) for r in rows})}


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--afgl',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    assets_dir=args.output/'assets'
    assets=extract_exact_assets(args.archive,assets_dir)
    reports={species:inspect_netcdf(assets_dir/f'{species}.cdf') for species in ASSETS}
    afgl=parse_afgl(args.afgl)
    if afgl['sha256']!='dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5':
        raise AuditError('AFGL-US SHA drift')
    report={
        'schemaVersion':1,
        'stageId':'opac-550nm-rh-optics-source-audit-v1',
        'status':'PASS_EXACT_OPAC_NETCDF_STRUCTURE_AND_AFGL_SOURCE_FROZEN',
        'archive':{'sha256':EXPECTED_ARCHIVE_SHA256,'byteCount':EXPECTED_ARCHIVE_SIZE,'memberCount':EXPECTED_ARCHIVE_MEMBERS},
        'assets':assets,
        'netcdf':reports,
        'afglUs':afgl,
        'uvspecInvoked':False,'syntaxCheckExecuted':False,'scientificSolverExecuted':False,
        'scientificOrdinalAllocated':False,'taylorOrJerusalemUsed':False,'productionAuthorized':False,
        'interpretationBoundary':'Source-structure audit only. Candidate variable detection is descriptive; no RH-selection or mass-to-extinction formula is authorized by this report.',
    }
    canonical=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    report['contentSha256']=hashlib.sha256(canonical).hexdigest()
    (args.output/'source-audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    # Preserve small human-readable headers but not duplicate the large cdf assets in the uploaded artifact.
    compact={
        'status':report['status'],'contentSha256':report['contentSha256'],'assets':assets,
        'candidateVariables':{s:r['candidateVariables'] for s,r in reports.items()},
        'dimensions':{s:r['dimensions'] for s,r in reports.items()},
        'afglSha256':afgl['sha256'],
    }
    print(json.dumps(compact,indent=2,sort_keys=True))

if __name__=='__main__':
    main()

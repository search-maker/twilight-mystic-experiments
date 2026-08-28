from __future__ import annotations
import importlib.util
import json
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('opac_v3_builder',HERE/'build_inputs.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def must_fail(fn, needle):
    try: fn()
    except Exception as e:
        assert needle in str(e), (needle,e)
    else: raise AssertionError('expected failure')


def main():
    assert m.STAGE_ID.endswith('-v3')
    assert m.SPECIES=='INSO' and m.AOD550==0.10 and m.MYSTIC_SEED==730_194_613 and m.MYSTIC_PHOTONS==500_000
    heights=(20.0,12.0,8.0,4.0,2.0,1.0,0.0)
    lo=m.synthetic_density_shape(heights,'low'); hi=m.synthetic_density_shape(heights,'high')
    assert lo!=hi and lo[-1]>lo[2] and hi[2]>hi[-1]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); data=root/'data'; repo=root/'repo'; out=root/'out'
        src=data/m.ALIAS_SOURCE_REL; src.parent.mkdir(parents=True); src.write_bytes(b'official-frozen-opac-inso-bytes\x00\x01')
        a=m.prepare_inso_alias(data)
        target=data/m.ALIAS_TARGET_REL
        assert target.read_bytes()==src.read_bytes()
        assert a['byteIdentical'] is True and a['sourceSha256']==a['aliasSha256'] and a['byteCount']==src.stat().st_size
        must_fail(lambda:m.prepare_inso_alias(data),'unexpectedly preexists')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); data=root/'data'; repo=root/'repo'; out=root/'out'
        src=data/m.ALIAS_SOURCE_REL; src.parent.mkdir(parents=True); src.write_bytes(b'official')
        target=data/m.ALIAS_TARGET_REL; target.write_bytes(b'wrong')
        must_fail(lambda:m.prepare_inso_alias(data),'unexpectedly preexists')
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); data=root/'data'; repo=root/'repo'; out=root/'out'
        (data/'atmmod').mkdir(parents=True); atm=data/'atmmod/afglus.dat'; atm.write_text('20 0\n12 0\n8 0\n4 0\n2 0\n1 0\n0 0\n')
        src=data/m.ALIAS_SOURCE_REL; src.parent.mkdir(parents=True); src.write_bytes(b'official-frozen-opac')
        (data/'solar_flux').mkdir(); (data/'solar_flux/atlas_plus_modtran').write_text('x')
        grid=repo/'experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat'; grid.parent.mkdir(parents=True); grid.write_text('540\n541\n')
        meta=m.write_bundle(atm,data,repo,out)
        assert meta['stageId']==m.STAGE_ID and meta['resolverAlias']['byteIdentical'] is True
        assert meta['scientificOrdinalAllocated'] is False and meta['taylorOrJerusalemUsed'] is False and meta['productionAuthorized'] is False
        for p in (out/'inputs').glob('*.inp'):
            t=p.read_text(); assert 'aerosol_species_file ' in t and ' INSO' in t and 'aerosol_set_tau_at_wvl 550 0.100000' in t
            assert 'aerosol_file tau' not in t and 'aerosol_file ssa' not in t and 'aerosol_file gg' not in t
        j=json.loads((out/'input-manifest.json').read_text()); assert j['resolverAlias']['sourceRelativePath']=='aerosol/OPAC/optprop/inso.mie.cdf'; assert j['resolverAlias']['aliasRelativePath']=='aerosol/OPAC/optprop/INSO.nc'
    print('opac species-profile transport capability v3: PASS')

if __name__=='__main__': main()

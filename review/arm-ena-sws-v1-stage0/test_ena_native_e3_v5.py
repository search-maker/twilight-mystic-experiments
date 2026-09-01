#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import netCDF4
import numpy as np

import ena_native_gate_core_v5 as G

START = 0.0
END = 120.0


def make_file(path: Path, *, shape_var: str | None = 'extinction', vertical=True, depol=False, cloud=False):
    with netCDF4.Dataset(path, 'w') as ds:
        ds.createDimension('time', 3)
        vdim = 'range' if vertical else 'level'
        ds.createDimension(vdim, 3)

        t = ds.createVariable('time', 'f8', ('time',))
        t.units = 'seconds since 1970-01-01 00:00:00 UTC'
        t[:] = [0.0, 60.0, 120.0]

        if vertical:
            z = ds.createVariable('range', 'f8', ('range',))
            z.units = 'm'
            z.long_name = 'height range above ground'
            z[:] = [30.0, 60.0, 90.0]

        f = ds.createVariable('feature_mask', 'i4', ('time', vdim))
        f[:] = np.full((3, 3), G.AEROSOL_BIT, dtype=np.int32)
        if cloud:
            a = np.full((3, 3), G.AEROSOL_BIT, dtype=np.int32)
            a[1, 1] |= 4
            f[:] = a

        if shape_var:
            s = ds.createVariable(shape_var, 'f8', ('time', vdim), fill_value=-9999.0)
            s[:] = np.arange(9, dtype=float).reshape(3, 3) + 1.0
            q = ds.createVariable('qc_' + shape_var, 'i4', ('time', vdim))
            q[:] = np.zeros((3, 3), dtype=np.int32)

        if depol:
            d = ds.createVariable('depolarization_ratio', 'f8', ('time', vdim), fill_value=-9999.0)
            d[:] = np.full((3, 3), 0.1)
            qd = ds.createVariable('qc_depolarization_ratio', 'i4', ('time', vdim))
            qd[:] = np.zeros((3, 3), dtype=np.int32)


def main():
    with tempfile.TemporaryDirectory(prefix='ena_e3_v5_') as td:
        root = Path(td)

        # QC-good aerosol extinction with a native vertical coordinate is a
        # valid retrieved shape basis and records native vertical support.
        p = root / 'good_extinction.nc'
        make_file(p, shape_var='extinction', vertical=True, depol=True)
        out = G.analyze_raman(p, START, END)
        assert out['e3_profile_usable'], out
        assert out['e3_shape_basis'] == 'extinction', out
        assert out['e3_vertical_coordinate'] == 'range', out
        assert out['e3_usable_vertical_level_count'] == 3, out

        # Backscatter is a shape-bearing vertical profile under the frozen E3
        # evidence family and can support the gate when extinction is absent.
        p = root / 'good_backscatter.nc'
        make_file(p, shape_var='backscatter', vertical=True)
        out = G.analyze_raman(p, START, END)
        assert out['e3_profile_usable'], out
        assert out['e3_shape_basis'] == 'backscatter', out

        # Depolarization alone was enough to trigger historical `any(c>0)` but
        # is not by itself a vertical extinction/backscatter shape to normalize
        # to independent column AOD. It must now fail closed.
        p = root / 'depol_only.nc'
        make_file(p, shape_var=None, vertical=True, depol=True)
        out = G.analyze_raman(p, START, END)
        assert not out['e3_profile_usable'], out
        assert out['reason'] == 'PROFILE_EVIDENCE_INSUFFICIENT', out

        # Array ordinal is not a native vertical coordinate. A QC-good optical
        # array on an unlabeled non-time dimension cannot establish the frozen
        # vertical-shape/common-support requirement.
        p = root / 'no_vertical_coordinate.nc'
        make_file(p, shape_var='extinction', vertical=False)
        out = G.analyze_raman(p, START, END)
        assert not out['e3_profile_usable'], out
        assert out['e3_vertical_support'], out
        assert out['e3_vertical_support'][0]['reason'] == 'VERTICAL_DIMENSION_MISSING_OR_AMBIGUOUS', out

        # E2 remains authoritative: a cloud-positive Raman feature can never be
        # promoted as E3 aerosol evidence even if extinction is otherwise valid.
        p = root / 'cloud.nc'
        make_file(p, shape_var='extinction', vertical=True, cloud=True)
        out = G.analyze_raman(p, START, END)
        assert out['cloud_positive'], out
        assert not out['e3_profile_usable'], out
        assert out['reason'] == 'CLOUD_OR_HYDROMETEOR_PRESENT', out

    print('PASS ENA native E3 v5 vertical-shape/common-support contracts')


if __name__ == '__main__':
    main()

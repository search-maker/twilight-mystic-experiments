#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('E6V2', HERE / 'ena_surface_gate_v2.py')
E6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E6)


class FakeVar:
    def __init__(self, data, name='', **attrs):
        self.data = np.ma.asarray(data)
        self.name = name
        self.__dict__.update(attrs)

    def __getitem__(self, key):
        return self.data[key]


class FakeDS:
    def __init__(self, variables):
        self.variables = variables


def response_ds(response_data=(0.0, 1.0, 0.0), response2_data=None):
    variables = {
        'hemisp_narrowband_filter2': FakeVar([1.0, 2.0], name='hemisp_narrowband_filter2'),
        # Deliberately includes 'spectral response' in metadata: this coordinate
        # must never be mistaken for the response function itself.
        'filter2_response_wavelength': FakeVar(
            [490.0, 500.0, 510.0],
            name='filter2_response_wavelength',
            units='nm',
            long_name='measured filter2 spectral response wavelength',
        ),
        'filter2_normalized_transmittance': FakeVar(
            response_data,
            name='filter2_normalized_transmittance',
            long_name='filter2 normalized transmittance spectral response',
        ),
    }
    if response2_data is not None:
        variables['filter2_filter_response_secondary'] = FakeVar(
            response2_data,
            name='filter2_filter_response_secondary',
            long_name='filter2 filter response secondary measured spectral response',
        )
    return FakeDS(variables)


def main():
    # One measured response pair establishes the response-weighted center.
    c = E6.measured_center_from_dataset(response_ds(), 2, 'hemisp_narrowband_filter2')
    assert c['ok'], c
    assert c['evidence_type'] == 'MEASURED_RESPONSE_WEIGHTED', c
    assert abs(c['center_nm'] - 500.0) < 1e-12, c
    # If the wavelength coordinate had been misclassified as a response
    # function, this would produce multiple/ambiguous proofs.
    assert len(c['proof_candidates']) == 1, c

    # Two same-level measured response proofs with different centers are
    # ambiguous and must fail closed; lower-level metadata may not rescue them.
    ds = response_ds(response2_data=(0.0, 0.0, 1.0))
    ds.variables['filter2_CWL_measured'] = FakeVar(
        [500.0], name='filter2_CWL_measured', units='nm',
        long_name='filter2 measured center wavelength',
    )
    c = E6.measured_center_from_dataset(ds, 2, 'hemisp_narrowband_filter2')
    assert not c['ok'], c
    assert c['reason'] == 'MEASURED_RESPONSE_SCHEMA_AMBIGUOUS', c

    # Consistent duplicate same-level proofs may corroborate rather than create
    # an artificial ambiguity.
    c = E6.measured_center_from_dataset(
        response_ds(response2_data=(0.0, 2.0, 0.0)),
        2, 'hemisp_narrowband_filter2'
    )
    assert c['ok'], c
    assert abs(c['center_nm'] - 500.0) < 1e-12, c
    assert c.get('corroborating_proof_count') == 2, c

    # Frozen hierarchy still permits an explicit measured-CWL scalar only when
    # there is no usable higher-level response proof.
    ds = FakeDS({
        'hemisp_narrowband_filter2': FakeVar([1.0, 2.0], name='hemisp_narrowband_filter2'),
        'filter2_CWL_measured': FakeVar(
            [500.1], name='filter2_CWL_measured', units='nm',
            long_name='measured center wavelength filter2',
        ),
    })
    c = E6.measured_center_from_dataset(ds, 2, 'hemisp_narrowband_filter2')
    assert c['ok'], c
    assert c['evidence_type'] == 'MEASURED_CWL_VARIABLE', c
    assert abs(c['center_nm'] - 500.1) < 1e-12, c

    # Conflicting measured-CWL variables at the same hierarchy are ambiguous.
    ds.variables['filter2_measured_centroid_wavelength'] = FakeVar(
        [503.0], name='filter2_measured_centroid_wavelength', units='nm',
        long_name='filter2 measured centroid wavelength',
    )
    c = E6.measured_center_from_dataset(ds, 2, 'hemisp_narrowband_filter2')
    assert not c['ok'], c
    assert c['reason'] == 'MEASURED_CWL_SCHEMA_AMBIGUOUS', c

    print('PASS ENA E6 v2 measured-wavelength ambiguity contracts')


if __name__ == '__main__':
    main()

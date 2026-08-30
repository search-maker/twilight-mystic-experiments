from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_finite_disk_exec001.py'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    mod = load_module('test_lunar_fd_exec001_runtime', RUNTIME)
    auth = mod.load_authorization()
    cases = mod.authorized_cases()
    assert auth['executionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001'
    assert len(cases) == 198
    assert len({row['caseId'] for row in cases}) == 198
    assert len({row['randomSeed'] for row in cases}) == 198
    assert all(not (32_910_001 <= row['randomSeed'] <= 32_910_198) for row in cases)
    assert {row['wavelengthNm'] for row in cases} == {550.0}
    assert {row['photonHistories'] for row in cases} == {5_000_000}
    assert {row['observerElevationM'] for row in cases} == {0.0, 2000.0}
    assert {row['targetRelativeAzimuthToMoonCenterDeg'] for row in cases} == {30.0, 90.0, 150.0}

    # Missing solver outputs must fail closed and may not become a finite-disk
    # validation or production claim.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        output = root / 'report.json'
        report = mod.evaluate_result_root(result_root=root, output_path=output)
        assert report['classification'] == 'EXECUTION_INCOMPLETE'
        assert report['executionComplete'] is False
        assert report['caseCountObserved'] == 0
        assert report['finiteMoonDiskValidated'] is False
        assert report['continuousDiskBoundProven'] is False
        assert report['physicalResolvedDiskIntegrationImplemented'] is False
        assert report['empiricalAtmosphericMoonlightValidated'] is False
        assert report['toaSourceValidated'] is False
        assert report['totalSkyValidated'] is False
        assert report['productionAuthorized'] is False
        assert report['resultDependentThresholdApplied'] is False
        assert report['mandatorySpectralFollowOnRequiredBeforeBroadbandFiniteDiskClaim'] is True
        assert report['mandatorySpectralFollowOnWavelengthsNm'] == [450.0, 650.0, 750.0]
        assert report['taylorOrJerusalemUsed'] is False
        assert report['seedLiteralsIncludedInReport'] is False
        on_disk = json.loads(output.read_text())
        assert on_disk['classification'] == 'EXECUTION_INCOMPLETE'

    print('lunar finite-disk exec001 runtime tests passed')


if __name__ == '__main__':
    main()

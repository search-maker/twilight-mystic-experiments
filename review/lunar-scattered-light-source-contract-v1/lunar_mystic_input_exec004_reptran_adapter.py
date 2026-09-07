#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parent / 'lunar-reptran-source-binding-prestage-v1' / 'lunar_mystic_input_reptran.py'
EXPECTED_UVSPEC_SHA256 = '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
EXPECTED_DATA_SHA256 = 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7'
CAPABILITY_RUN = 34053349932
CAPABILITY_JOB = 101540778940
CAPABILITY_ARTIFACT = 9995224987
CAPABILITY_DIGEST = 'sha256:fd906b1060594a6e80884f3847e4fdcc43e8ede7f231d04cfe797fbcf4204e79'

class LunarExec004ReptranError(RuntimeError):
    pass

def _core():
    spec=importlib.util.spec_from_file_location('lunar_exec004_reptran_core', CORE_PATH)
    if spec is None or spec.loader is None:
        raise LunarExec004ReptranError('reviewed REPTRAN core unavailable')
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def _require_runtime_identity(runtime_identity: dict | None) -> None:
    if not isinstance(runtime_identity, dict):
        raise LunarExec004ReptranError('exact runtime identity required')
    if runtime_identity.get('uvspecSha256') != EXPECTED_UVSPEC_SHA256:
        raise LunarExec004ReptranError('uvspec runtime identity drift')
    if runtime_identity.get('libRadtranDataTreeSha256') != EXPECTED_DATA_SHA256:
        raise LunarExec004ReptranError('libRadtran data-tree identity drift')

def render_lunar_mystic_input(*, data_dir: Path, atmosphere_file: Path, lunar_source_file: Path,
    moon_zenith_deg: float, target_altitude_deg: float, target_relative_azimuth_to_moon_deg: float,
    observer_elevation_m: float, aod550: float, albedo: float, photon_histories: int,
    random_seed: int, case_dir: Path, runtime_identity: dict | None = None,
    alis_importance_nm: float = 550.0):
    _require_runtime_identity(runtime_identity)
    core=_core()
    text, meta=core.render_lunar_mystic_reptran_prestage(
        data_dir=data_dir, atmosphere_file=atmosphere_file, lunar_source_file=lunar_source_file,
        moon_zenith_deg=moon_zenith_deg, target_altitude_deg=target_altitude_deg,
        target_relative_azimuth_to_moon_deg=target_relative_azimuth_to_moon_deg,
        observer_elevation_m=observer_elevation_m, aod550=aod550, albedo=albedo,
        photon_histories=photon_histories, synthetic_review_seed=random_seed, case_dir=case_dir,
        alis_importance_nm=alis_importance_nm)
    core.validate_rendered_reptran_input(text, lunar_source_file)
    if text.splitlines().count('mol_abs_param reptran') != 1:
        raise LunarExec004ReptranError('REPTRAN directive count drift')
    if any(line.startswith('mol_abs_param crs') for line in text.splitlines()):
        raise LunarExec004ReptranError('CRS fallback forbidden')
    return text, {
        **meta,
        'finiteMoonDiskModeled': False,
        'customSourceReptranConsumptionCapabilityVerified': True,
        'customSourceReptranCapabilityRun': CAPABILITY_RUN,
        'customSourceReptranCapabilityJob': CAPABILITY_JOB,
        'customSourceReptranCapabilityArtifact': CAPABILITY_ARTIFACT,
        'customSourceReptranCapabilityDigest': CAPABILITY_DIGEST,
        'atmosphericScatteredMoonlightValidated': False,
        'validatedForAtmosphericScatteredMoonlight': False,
        'productionAuthorized': False,
    }

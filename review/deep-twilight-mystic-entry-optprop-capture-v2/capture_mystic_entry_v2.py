#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

STAGE_ID = "deep-twilight-mystic-entry-optprop-capture-v2"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
EXPECTED_SEED = 1173101368
EXPECTED_WAVELENGTH_NM = 550.0
EXPECTED_AOD550 = 0.150000
EXPECTED_BARE_N_CAOTH = 2
MAX_NLYR = 512


class CaptureError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run_metadata(command: Sequence[str], output: Path) -> dict[str, Any]:
    process = subprocess.run(list(command), text=True, capture_output=True, check=False, timeout=60)
    text = process.stdout + process.stderr
    output.write_text(text, encoding="utf-8")
    return {
        "command": list(command),
        "exitCode": process.returncode,
        "path": output.name,
        "sha256": sha256_file(output),
    }


def exact_symbol_addresses(nm_text: str, symbol: str) -> list[str]:
    addresses: list[str] = []
    pattern = re.compile(rf"^([0-9A-Fa-f]+)\s+\S\s+{re.escape(symbol)}$")
    for raw in nm_text.splitlines():
        match = pattern.match(raw.strip())
        if match:
            addresses.append(match.group(1).lower())
    return sorted(set(addresses))


def build_input(data_dir: Path, atmosphere: Path, solar_flux: Path, output_dir: Path) -> str:
    # Setup-only capture. The debugger stops at the first instruction of mystic() and
    # kills the inferior before the MYSTIC body executes. The explicitly frozen seed
    # is nevertheless considered consumed as soon as uvspec initializes its RNG.
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {atmosphere.resolve()}",
        f"source solar {solar_flux.resolve()}",
        "mol_abs_param crs",
        f"wavelength {EXPECTED_WAVELENGTH_NM:.1f} {EXPECTED_WAVELENGTH_NM:.1f}",
        "sza 80.000000",
        "phi0 0.000000",
        "albedo 0.150000",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {EXPECTED_AOD550:.6f}",
        "rte_solver mystic",
        "mc_spherical 1D",
        "mc_photons 1",
        "mc_vroom off",
        "mc_std",
        f"mc_randomseed {EXPECTED_SEED}",
        "mc_basename mc",
        f"mc_spectral_is {EXPECTED_WAVELENGTH_NM:.1f}",
        "zout 0.000000",
        "umu -0.50000000",
        "phi 36.000000",
        "quiet",
        "",
    ]
    text = "\n".join(lines)
    actual = text.splitlines()
    frozen_singletons = {
        "aerosol_default": 1,
        "aerosol_set_tau_at_wvl 550 0.150000": 1,
        "rte_solver mystic": 1,
        f"mc_randomseed {EXPECTED_SEED}": 1,
        "mc_basename mc": 1,
    }
    for directive, count in frozen_singletons.items():
        if actual.count(directive) != count:
            raise CaptureError(f"frozen directive cardinality drift: {directive!r}")
    random_seed_lines = [line for line in actual if line.startswith("mc_randomseed ")]
    if random_seed_lines != [f"mc_randomseed {EXPECTED_SEED}"]:
        raise CaptureError(f"unexpected seed directives: {random_seed_lines}")
    return text


def _json_safe_float(value: float) -> str | float:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def run_gdb_hook(output_path: str) -> None:
    """Executed inside GDB at exact `break *mystic` before any callee instruction."""
    import gdb  # type: ignore

    out = Path(output_path)
    inferior = gdb.selected_inferior()
    arch = gdb.selected_frame().architecture().name()
    if "x86-64" not in arch:
        raise gdb.GdbError(f"unexpected architecture: {arch}")

    def reg(name: str) -> int:
        return int(gdb.parse_and_eval(f"${name}"))

    def read(addr: int, size: int) -> bytes:
        if addr <= 0:
            raise gdb.GdbError(f"null/invalid address 0x{addr:x}")
        return bytes(inferior.read_memory(addr, size))

    def u64(addr: int) -> int:
        return struct.unpack("<Q", read(addr, 8))[0]

    pc = reg("pc")
    rsp = reg("rsp")
    symbol_addr = int(gdb.parse_and_eval("(unsigned long)&mystic"))
    if pc != symbol_addr:
        raise gdb.GdbError(f"not stopped at exact mystic entry: pc=0x{pc:x} symbol=0x{symbol_addr:x}")

    # Exact package ABI evidence from the immutable static V3 probe shows:
    #   rdi -> pointer-width arg 1, rsi -> pointer-width arg 2,
    #   edx -> 32-bit arg 3, rcx/r8/r9 -> pointer-width args 4/5/6,
    #   and the callee loads the first spilled pointer from original rsp+8.
    # The official 2.0.6 source currently served by libRadtran (archive hash is NOT
    # accepted as the historical conda source hash) independently corroborates the
    # semantic prefix:
    #   int *nlyr, int *threed, int n_caoth, float **dt_s, float **om_s,
    #   float **g1_s, float **g2_s, float **f_s, float **ds_s, ...
    # We capture raw bits first and retain this semantic mapping as explicit provenance.
    nlyr_ptr = reg("rdi")
    threed_ptr = reg("rsi")
    n_caoth = reg("rdx") & 0xFFFFFFFF
    dt_table = reg("rcx")
    om_table = reg("r8")
    g1_table = reg("r9")
    g2_table = u64(rsp + 0x08)
    f_table = u64(rsp + 0x10)
    ds_table = u64(rsp + 0x18)
    zprof_ptr = u64(rsp + 0x58)

    nlyr = struct.unpack("<i", read(nlyr_ptr, 4))[0]
    if not (1 <= nlyr <= MAX_NLYR):
        raise gdb.GdbError(f"implausible nlyr={nlyr}")
    if n_caoth != EXPECTED_BARE_N_CAOTH:
        raise gdb.GdbError(f"bare aerosol_default expected n_caoth={EXPECTED_BARE_N_CAOTH}, got {n_caoth}")

    def capture_float32_vector(label: str, addr: int, count: int) -> dict[str, Any]:
        raw = read(addr, 4 * count)
        words = list(struct.unpack("<" + "I" * count, raw))
        floats = list(struct.unpack("<" + "f" * count, raw))
        return {
            "label": label,
            "addressHex": f"0x{addr:016x}",
            "rawBytesHex": raw.hex(),
            "rawSha256": hashlib.sha256(raw).hexdigest(),
            "uint32Words": [f"0x{word:08x}" for word in words],
            "decodedFloat32AuditOnly": [_json_safe_float(value) for value in floats],
            "positiveZeroCount": sum(word == 0x00000000 for word in words),
            "negativeZeroCount": sum(word == 0x80000000 for word in words),
        }

    def capture_int32_vector(label: str, addr: int, count: int) -> dict[str, Any]:
        raw = read(addr, 4 * count)
        values = list(struct.unpack("<" + "i" * count, raw))
        return {
            "label": label,
            "addressHex": f"0x{addr:016x}",
            "rawBytesHex": raw.hex(),
            "rawSha256": hashlib.sha256(raw).hexdigest(),
            "int32ValuesAuditOnly": values,
        }

    def capture_table(label: str, table_addr: int) -> dict[str, Any]:
        raw_table = read(table_addr, 8 * n_caoth)
        ptrs = list(struct.unpack("<" + "Q" * n_caoth, raw_table))
        rows: list[dict[str, Any]] = []
        for index, row_addr in enumerate(ptrs):
            if row_addr == 0:
                raise gdb.GdbError(f"{label}[{index}] row pointer is null")
            row = capture_float32_vector(f"{label}[{index}]", row_addr, nlyr)
            row["index"] = index
            rows.append(row)
        return {
            "tableAddressHex": f"0x{table_addr:016x}",
            "pointerTableRawBytesHex": raw_table.hex(),
            "pointerTableRawSha256": hashlib.sha256(raw_table).hexdigest(),
            "rowPointersHex": [f"0x{ptr:016x}" for ptr in ptrs],
            "rows": rows,
        }

    dt_capture = capture_table("dt_s", dt_table)
    aerosol_dt_values = dt_capture["rows"][1]["decodedFloat32AuditOnly"]
    finite_aerosol_dt = [float(value) for value in aerosol_dt_values if not isinstance(value, str)]

    payload = {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": "EXACT_MYSTIC_ENTRY_RAW_OPTICAL_STATE_CAPTURED",
        "architecture": arch,
        "stoppedAtExactMysticEntry": True,
        "mysticBodyExecuted": False,
        "photonTraced": False,
        "scientificDatasetProduced": False,
        "randomSeed": EXPECTED_SEED,
        "randomSeedConsumed": True,
        "rawBitsAuthoritative": True,
        "decodedValuesAuditOnly": True,
        "verbosePrintedZerosAuthoritative": False,
        "pcHex": f"0x{pc:016x}",
        "rspAtEntryHex": f"0x{rsp:016x}",
        "mysticSymbolAddressHex": f"0x{symbol_addr:016x}",
        "abiMapping": {
            "arg1_rdi": "int *nlyr",
            "arg2_rsi": "int *threed",
            "arg3_edx": "int n_caoth",
            "arg4_rcx": "float **dt_s",
            "arg5_r8": "float **om_s",
            "arg6_r9": "float **g1_s",
            "stack_rsp_plus_0x08": "float **g2_s",
            "stack_rsp_plus_0x10": "float **f_s",
            "stack_rsp_plus_0x18": "float **ds_s",
            "stack_rsp_plus_0x58": "float *zprof",
        },
        "nlyrPointerHex": f"0x{nlyr_ptr:016x}",
        "threedPointerHex": f"0x{threed_ptr:016x}",
        "nlyr": nlyr,
        "nCaoth": n_caoth,
        "threed": capture_int32_vector("threed", threed_ptr, nlyr),
        "zprof": capture_float32_vector("zprof", zprof_ptr, nlyr + 1),
        "tables": {
            "dt_s": dt_capture,
            "om_s": capture_table("om_s", om_table),
            "g1_s": capture_table("g1_s", g1_table),
            "g2_s": capture_table("g2_s", g2_table),
            "f_s": capture_table("f_s", f_table),
            "ds_s": capture_table("ds_s", ds_table),
        },
        "aerosolRowIndexCandidate": 1,
        "aerosolDtFloat64SumAuditOnly": sum(finite_aerosol_dt),
    }
    json_dump(out, payload)


def make_gdb_command(script_path: Path, input_path: Path, capture_path: Path) -> str:
    module_dir = script_path.resolve().parent
    return "\n".join(
        [
            "set pagination off",
            "set confirm off",
            "set print thread-events off",
            "set debuginfod enabled off",
            "set breakpoint pending off",
            "set disable-randomization off",
            "handle SIGPIPE nostop noprint pass",
            "break *mystic",
            f"run < {input_path.resolve()}",
            "python",
            "import sys",
            f"sys.path.insert(0, {str(module_dir)!r})",
            "import capture_mystic_entry_v2 as capture",
            f"capture.run_gdb_hook({str(capture_path.resolve())!r})",
            "end",
            "kill",
            "quit",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", required=True)
    parser.add_argument("--gdb", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--atmosphere", required=True)
    parser.add_argument("--solar-flux", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-explicit")
    parser.add_argument("--package-json")
    args = parser.parse_args()

    uvspec = Path(args.uvspec).resolve()
    gdb = Path(args.gdb).resolve()
    data_dir = Path(args.data_dir).resolve()
    atmosphere = Path(args.atmosphere).resolve()
    solar_flux = Path(args.solar_flux).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for path, label in ((uvspec, "uvspec"), (gdb, "gdb"), (atmosphere, "atmosphere"), (solar_flux, "solar flux")):
        if not path.is_file():
            raise CaptureError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise CaptureError(f"data directory missing: {data_dir}")

    uvspec_hash = sha256_file(uvspec)
    if uvspec_hash != EXPECTED_UVSPEC_SHA256:
        raise CaptureError(f"uvspec SHA mismatch: {uvspec_hash}")

    metadata: dict[str, Any] = {
        "file": run_metadata(["file", str(uvspec)], output_dir / "uvspec-file.txt"),
        "readelf": run_metadata(["readelf", "-h", "-Ws", str(uvspec)], output_dir / "uvspec-readelf.txt"),
        "nm": run_metadata(["nm", "-an", str(uvspec)], output_dir / "uvspec-nm.txt"),
        "objdumpMystic": run_metadata(["objdump", "-d", "-Mintel", "--disassemble=mystic", str(uvspec)], output_dir / "uvspec-mystic-objdump.txt"),
        "gdbVersion": run_metadata([str(gdb), "--version"], output_dir / "gdb-version.txt"),
    }
    file_text = (output_dir / "uvspec-file.txt").read_text(encoding="utf-8")
    if "x86-64" not in file_text and "x86_64" not in file_text:
        raise CaptureError("exact runtime is not x86-64")
    nm_text = (output_dir / "uvspec-nm.txt").read_text(encoding="utf-8")
    symbol_addresses = exact_symbol_addresses(nm_text, "mystic")
    if len(symbol_addresses) != 1:
        raise CaptureError(f"expected one unique exact mystic symbol address, found {symbol_addresses}")

    objdump_text = (output_dir / "uvspec-mystic-objdump.txt").read_text(encoding="utf-8")
    required_machine_evidence = [
        "mov    QWORD PTR [rsp+0x60],rdi",
        "mov    QWORD PTR [rsp+0x208],rsi",
        "mov    DWORD PTR [rsp+0x78],edx",
        "mov    QWORD PTR [rsp+0x188],rcx",
        "mov    QWORD PTR [rsp+0x198],r8",
        "mov    QWORD PTR [rsp+0x1a0],r9",
        "mov    rax,QWORD PTR [rsp+0x400]",
    ]
    missing = [needle for needle in required_machine_evidence if needle not in objdump_text]
    if missing:
        raise CaptureError(f"exact-binary ABI prologue evidence drift: missing {missing}")

    input_text = build_input(data_dir, atmosphere, solar_flux, output_dir)
    input_path = output_dir / "input-resolved.txt"
    input_path.write_text(input_text, encoding="utf-8")
    capture_path = output_dir / "mystic-entry-raw-v2.json"
    command_path = output_dir / "capture-v2.gdb"
    command_path.write_text(make_gdb_command(Path(__file__), input_path, capture_path), encoding="utf-8")

    started = time.monotonic()
    try:
        process = subprocess.run(
            [str(gdb), "-q", "-nx", "--batch", "-x", str(command_path), "--args", str(uvspec)],
            cwd=output_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
            env=os.environ.copy(),
        )
        timed_out = False
        returncode = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    elapsed = time.monotonic() - started
    (output_dir / "gdb-stdout.txt").write_text(stdout, encoding="utf-8")
    (output_dir / "gdb-stderr.txt").write_text(stderr, encoding="utf-8")

    if timed_out:
        raise CaptureError("GDB capture timed out")
    if returncode != 0:
        raise CaptureError(f"GDB capture failed with exit code {returncode}: {stderr[-3000:]}")
    if not capture_path.is_file():
        raise CaptureError("raw capture JSON missing")

    seed_file = output_dir / "randomseed"
    if not seed_file.is_file():
        raise CaptureError("uvspec did not persist the explicit consumed randomseed before MYSTIC entry")
    seed_first_line = seed_file.read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
    if seed_first_line != str(EXPECTED_SEED):
        raise CaptureError(f"unexpected persisted randomseed: {seed_first_line!r}")

    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    if capture.get("status") != "EXACT_MYSTIC_ENTRY_RAW_OPTICAL_STATE_CAPTURED":
        raise CaptureError("unexpected capture status")
    if capture.get("stoppedAtExactMysticEntry") is not True or capture.get("mysticBodyExecuted") is not False:
        raise CaptureError("entry/body execution boundary not proven")
    if capture.get("randomSeed") != EXPECTED_SEED or capture.get("randomSeedConsumed") is not True:
        raise CaptureError("fresh seed consumption semantics not frozen")

    package_files: dict[str, Any] = {}
    for label, raw in (("explicit", args.package_explicit), ("json", args.package_json)):
        if raw:
            path = Path(raw).resolve()
            if not path.is_file():
                raise CaptureError(f"package identity file missing: {path}")
            package_files[label] = {"path": path.name, "sha256": sha256_file(path), "sizeBytes": path.stat().st_size}

    summary = {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": "PASS_EXACT_MYSTIC_ENTRY_RAW_OPTICAL_STATE_ACCESSIBLE",
        "claimBoundary": "lossless final pre-MYSTIC dt_s/om_s/g1_s/g2_s/f_s/ds_s plus threed/zprof ABI capture for frozen bare aerosol_default state; semantic row translation remains a separate parity gate; no photon/science result",
        "uvspecSha256": uvspec_hash,
        "expectedPackage": EXPECTED_PACKAGE,
        "inputSha256": sha256_file(input_path),
        "captureSha256": sha256_file(capture_path),
        "randomSeed": EXPECTED_SEED,
        "randomSeedConsumed": True,
        "randomseedFileSha256": sha256_file(seed_file),
        "nlyr": capture["nlyr"],
        "nCaoth": capture["nCaoth"],
        "mysticSymbolStaticAddressHex": symbol_addresses[0],
        "mysticSymbolRuntimeAddressHex": capture["mysticSymbolAddressHex"],
        "elapsedSeconds": elapsed,
        "metadata": metadata,
        "packageIdentityFiles": package_files,
        "mysticBodyExecuted": False,
        "photonTraced": False,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "protectedResultOpened": False,
        "levelBChanged": False,
        "taylorOrJerusalemUsed": False,
        "epsilonSubstitutionUsed": False,
        "githubRerunPermitted": False,
        "predecessorV1Run": 34011919740,
        "predecessorV1ImplicitSeed": 1788672559,
        "predecessorV1ImplicitSeedReusable": False,
    }
    json_dump(output_dir / "capture-summary-v2.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

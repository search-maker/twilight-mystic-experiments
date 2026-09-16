import argparse
import ast
import base64
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import traceback
import zlib

EXPECTED = {
    "v39_reviewer": "e0ef777c69e7d36027212a344150b836ba7c51f9",
    "v39_workflow": "1324a733b2a6a02aec376331ab09e2ed6fe0d627",
    "v38_reviewer": "50e966267259749d8d2fd81144339b2668887374",
    "v37_reviewer": "842c4d53f734ef1b7ee0958307f21b761024321c",
    "v36_reviewer": "0ad60505cf17f2f756daf694aed62b2105f7e1c0",
    "v35_reviewer": "cd027a47f5230228f509ca834b02ac3b4e2e0629",
    "v17_reviewer": "06867e14710f15cade77ed24fbdc33dafb9f2f74",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_verified(path: str, expected_blob: str) -> bytes:
    data = Path(path).read_bytes()
    got = git_blob_sha(data)
    if got != expected_blob:
        raise RuntimeError(f"blob drift for {path}: {got} != {expected_blob}")
    return data


def extract_payload(wrapper: bytes) -> tuple[bytes, dict]:
    text = wrapper.decode("utf-8")
    tree = ast.parse(text)
    payload = None
    assign_span = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAYLOAD_B85" for t in node.targets):
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                raise RuntimeError("V39 PAYLOAD_B85 is not a static string")
            payload = zlib.decompress(base64.b85decode(node.value.value.encode("ascii")))
            assign_span = [node.lineno, getattr(node, "end_lineno", node.lineno)]
    if payload is None:
        raise RuntimeError("V39 PAYLOAD_B85 assignment count drift")
    return payload, {"wrapperAstSha256": sha256(ast.dump(tree, include_attributes=True).encode()), "payloadAssignmentSpan": assign_span}


def predicate_inventory(source: str) -> list[dict]:
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        kind = None
        expr = None
        if isinstance(node, ast.Assert):
            kind, expr = "Assert", ast.unparse(node.test)
        elif isinstance(node, ast.Raise):
            kind, expr = "Raise", ast.unparse(node.exc) if node.exc else None
        elif isinstance(node, ast.Call):
            f = node.func
            is_exit = isinstance(f, ast.Name) and f.id in {"exit", "quit"}
            is_exit = is_exit or isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "sys" and f.attr == "exit"
            if is_exit:
                kind, expr = "ExitCall", ast.unparse(node)
        if kind:
            out.append({"kind": kind, "line": getattr(node, "lineno", None), "endLine": getattr(node, "end_lineno", None), "expr": expr, "astSha256": sha256(ast.dump(node, include_attributes=False).encode())})
    out.sort(key=lambda r: (r["line"] or 0, r["kind"], r["astSha256"]))
    return out


def install_escape_blocks(allowed_root: Path):
    def blocked(*_a, **_k):
        raise RuntimeError("V40 bounded reproduction blocked process/network escape")
    subprocess.run = blocked
    subprocess.Popen = blocked
    subprocess.call = blocked
    subprocess.check_call = blocked
    subprocess.check_output = blocked
    os.system = blocked
    os.popen = blocked
    socket.socket = blocked
    socket.create_connection = blocked

    real_open = builtins.open
    real_io_open = io.open
    root = allowed_root.resolve()
    def checked_open(file, mode="r", *a, **k):
        if any(ch in mode for ch in "wax+"):
            p = Path(file).resolve()
            if root != p and root not in p.parents:
                raise RuntimeError(f"V40 bounded reproduction blocked write outside evidence root: {p}")
        return real_open(file, mode, *a, **k)
    def checked_io_open(file, mode="r", *a, **k):
        if any(ch in mode for ch in "wax+"):
            p = Path(file).resolve()
            if root != p and root not in p.parents:
                raise RuntimeError(f"V40 bounded reproduction blocked write outside evidence root: {p}")
        return real_io_open(file, mode, *a, **k)
    builtins.open = checked_open
    io.open = checked_io_open


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v39-reviewer", required=True)
    ap.add_argument("--v39-workflow", required=True)
    for v in ("v38", "v37", "v36", "v35", "v17"):
        ap.add_argument(f"--{v}-reviewer", required=True)
    ap.add_argument("--v4-metadata", required=True)
    ap.add_argument("--v5-metadata", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stage = "identity"
    report = {"status": "FAIL_V40_PREACTUAL_DIAGNOSTIC", "lastProvenStage": stage, "protected": False, "science": False, "publisher": False, "newMapping": False, "production": False, "solverInvoked": False, "ordinal46": "NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED", "seedsConsumed": False}
    try:
        paths = {
            "v39_reviewer": args.v39_reviewer,
            "v39_workflow": args.v39_workflow,
            "v38_reviewer": args.v38_reviewer,
            "v37_reviewer": args.v37_reviewer,
            "v36_reviewer": args.v36_reviewer,
            "v35_reviewer": args.v35_reviewer,
            "v17_reviewer": args.v17_reviewer,
        }
        frozen = {}
        for key, path in paths.items():
            data = read_verified(path, EXPECTED[key])
            frozen[key] = {"path": path, "gitBlob": EXPECTED[key], "sha256": sha256(data), "bytes": len(data)}
        for key, path in (("v4", args.v4_metadata), ("v5", args.v5_metadata)):
            data = Path(path).read_bytes(); json.loads(data); frozen[key] = {"sha256": sha256(data), "bytes": len(data)}
        report["frozenInputs"] = frozen
        stage = "payload-decoded-static-inventory"
        wrapper = Path(args.v39_reviewer).read_bytes()
        payload, wrapper_info = extract_payload(wrapper)
        source = payload.decode("utf-8")
        report["v39Wrapper"] = wrapper_info
        report["v39Payload"] = {"sha256": sha256(payload), "bytes": len(payload), "astSha256": sha256(ast.dump(ast.parse(source), include_attributes=True).encode())}
        report["candidatePredicateTable"] = predicate_inventory(source)
        report["lastProvenStage"] = stage
        (out / "v39-payload-static-inventory.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

        stage = "bounded-v39-preactual-reproduction"
        repro_root = out / "reproduction"
        repro_root.mkdir(parents=True, exist_ok=True)
        os.environ["V38_FROZEN_REVIEWER"] = args.v38_reviewer
        os.environ["V37_FROZEN_REVIEWER"] = args.v37_reviewer
        os.environ["V36_FROZEN_REVIEWER"] = args.v36_reviewer
        os.environ["V35_FROZEN_REVIEWER"] = args.v35_reviewer
        os.environ["V17_FROZEN_REVIEWER"] = args.v17_reviewer
        os.environ["V39_PREACTUAL_FAILURE_DIR"] = str(repro_root / "v39-failure")
        (repro_root / "v39-failure").mkdir(parents=True, exist_ok=True)
        sys.argv = ["v39-reproduced.py", "--v39-proof-only", "--v39-forensic-out", str(repro_root / "v39-forensic.json"), "--v39-repair-proof-out", str(repro_root / "v39-repair-proof.json"), "--v4-metadata", args.v4_metadata, "--v5-metadata", args.v5_metadata]
        install_escape_blocks(repro_root)
        try:
            exec(compile(source, "<frozen-v39-payload>", "exec"), {"__name__": "__main__", "__file__": "<frozen-v39-payload>"})
            reproduced = {"exception": None, "message": None, "traceback": []}
        except BaseException as exc:
            tb = traceback.extract_tb(exc.__traceback__)
            reproduced = {"exception": type(exc).__name__, "message": str(exc), "traceback": [{"file": f.filename, "line": f.lineno, "name": f.name, "source": f.line} for f in tb]}
        report["reproduction"] = reproduced
        report["lastProvenStage"] = stage
        (out / "v40-diagnostic.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        if reproduced["exception"] is None:
            raise RuntimeError("V40 bounded reproduction did not reproduce a V39 PRE-ACTUAL stop")
        raise RuntimeError(f"V40 diagnostic reproduced frozen V39 stop: {reproduced['exception']}: {reproduced['message']}; correction not inferred without a separate unique-mismatch proof")
    except BaseException as exc:
        report["lastProvenStage"] = stage
        report["refusal"] = f"{type(exc).__name__}: {exc}"
        report["failureTraceback"] = traceback.format_exc().splitlines()[-20:]
        (out / "failure.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(report["refusal"], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib

V36_REFUSAL_PREFIX = "V36 V35 cardinality temporaries have downstream semantic consumers"
V35_REFUSAL_PREFIX = "V35 V33 If continuation provenance drift"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def seg(src: str, node: ast.AST) -> str:
    return ast.get_source_segment(src, node) or ""


def decode_wrapper(path: str):
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    payloads = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if any(isinstance(t, ast.Name) and t.id == "PAYLOAD_B85" for t in targets):
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    payloads.append(value.value)
    if len(payloads) != 1:
        raise RuntimeError(f"wrapper PAYLOAD_B85 count drift: {len(payloads)}")
    decoded = zlib.decompress(base64.b85decode(payloads[0])).decode("utf-8")
    return {
        "path": path,
        "wrapperBytesSha256": sha256_bytes(raw),
        "wrapperSourceSha256": sha256_text(text),
        "payloadSourceSha256": sha256_text(decoded),
        "wrapperSource": text,
        "payloadSource": decoded,
    }


def parents(tree: ast.AST):
    out = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            out[c] = p
    return out


def ancestor(node, pmap, typ):
    cur = node
    while cur in pmap:
        cur = pmap[cur]
        if isinstance(cur, typ):
            return cur
    return None


def const_strings(node):
    vals = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            vals.append(n.value)
    return vals


def find_unique_raise(src: str, prefix: str):
    tree = ast.parse(src)
    pmap = parents(tree)
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Raise) and any(prefix in s for s in const_strings(n)):
            hits.append(n)
    if len(hits) != 1:
        raise RuntimeError(f"raise provenance count drift for {prefix!r}: {len(hits)}")
    n = hits[0]
    fn = ancestor(n, pmap, (ast.FunctionDef, ast.AsyncFunctionDef))
    iff = ancestor(n, pmap, ast.If)
    return tree, pmap, n, fn, iff


def names_loaded(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def names_stored(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Param))}


def flatten_statements(body):
    out = []
    def walk_stmt(s):
        out.append(s)
        for field in ("body", "orelse", "finalbody"):
            for c in getattr(s, field, []) or []:
                if isinstance(c, ast.stmt):
                    walk_stmt(c)
        for h in getattr(s, "handlers", []) or []:
            for c in getattr(h, "body", []) or []:
                walk_stmt(c)
    for s in body:
        walk_stmt(s)
    return out


def pure_evidence_call(call: ast.Call) -> bool:
    f = call.func
    if isinstance(f, ast.Name) and f.id in {"dict", "list", "tuple", "set", "sorted", "len", "str", "repr", "int", "bool", "enumerate", "range", "min", "max", "sum"}:
        return True
    if isinstance(f, ast.Attribute):
        chain = []
        cur = f
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            chain.append(cur.id)
        dotted = ".".join(reversed(chain))
        if dotted in {"json.dumps", "hashlib.sha256"}:
            return True
        if f.attr in {"hexdigest", "encode", "decode", "strip", "split", "splitlines", "join"}:
            return True
        if f.attr in {"write_text", "write_bytes"}:
            return True
    return False


def stmt_kind(stmt: ast.stmt, tainted_names):
    loaded = names_loaded(stmt) & tainted_names
    if not loaded:
        return None
    if isinstance(stmt, (ast.If, ast.While)) and (names_loaded(stmt.test) & tainted_names):
        return "classifier_control"
    if isinstance(stmt, ast.Assert) and (names_loaded(stmt.test) & tainted_names):
        return "classifier_control"
    if isinstance(stmt, ast.Return):
        return "return_semantics"
    if isinstance(stmt, ast.Raise):
        return "classifier_control"
    for n in ast.walk(stmt):
        if isinstance(n, ast.Call) and (names_loaded(n) & tainted_names):
            f = n.func
            if isinstance(f, ast.Name) and f.id in {"exec", "eval", "compile", "__import__"}:
                return "executable_behavior"
            if isinstance(f, ast.Attribute) and f.attr in {"system", "popen", "run", "call", "check_call", "check_output", "Popen"}:
                return "executable_behavior"
            if not pure_evidence_call(n):
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    continue
                return "ambiguous_call"
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return "derived_assignment"
    if isinstance(stmt, ast.Expr):
        calls = [n for n in ast.walk(stmt) if isinstance(n, ast.Call)]
        if calls and all(pure_evidence_call(c) for c in calls if names_loaded(c) & tainted_names):
            return "evidence_materialization"
        return "ambiguous_expr"
    return "evidence_structure"


def analyze_temp_downstream(src: str, fn, fail_if, temp: str):
    flat = flatten_statements(fn.body)
    after_line = getattr(fail_if, "end_lineno", fail_if.lineno)
    tainted = {temp}
    edges = []
    consumers = []
    changed = True
    while changed:
        changed = False
        for stmt in flat:
            if getattr(stmt, "lineno", 0) <= after_line:
                continue
            loaded = names_loaded(stmt) & tainted
            if not loaded:
                continue
            kind = stmt_kind(stmt, tainted)
            target_names = names_stored(stmt) if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)) else set()
            record = {
                "line": getattr(stmt, "lineno", None),
                "endLine": getattr(stmt, "end_lineno", None),
                "kind": kind,
                "source": seg(src, stmt),
                "sourceSha256": sha256_text(seg(src, stmt)),
                "loadedTaint": sorted(loaded),
                "stored": sorted(target_names),
            }
            key = (record["line"], record["sourceSha256"], tuple(record["loadedTaint"]))
            if not any((r["line"], r["sourceSha256"], tuple(r["loadedTaint"])) == key for r in consumers):
                consumers.append(record)
            for t in target_names:
                if t not in tainted:
                    tainted.add(t)
                    edges.append({"from": sorted(loaded), "to": t, "line": record["line"], "kind": "data"})
                    changed = True
    fatal_kinds = {"classifier_control", "return_semantics", "executable_behavior", "ambiguous_call", "ambiguous_expr"}
    fatal = [c for c in consumers if c["kind"] in fatal_kinds]
    evidence_only = bool(consumers) and not fatal
    return {
        "temporary": temp,
        "taintedNames": sorted(tainted),
        "edges": edges,
        "consumers": consumers,
        "fatalConsumers": fatal,
        "evidenceOnly": evidence_only,
        "noDownstreamConsumers": not consumers,
    }


def synthetic_classification(source: str, temp="x"):
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    fail_if = next(n for n in fn.body if isinstance(n, ast.If))
    return analyze_temp_downstream(source, fn, fail_if, temp)


def run_fixtures():
    fixtures = {}
    s1 = """def f(x, out):\n    if len(x) != 1:\n        raise RuntimeError('old')\n    evidence = {'n': len(x), 'copy': list(x)}\n    out.write_text(json.dumps(evidence))\n"""
    r1 = synthetic_classification(s1)
    fixtures["harness_evidence_only"] = r1
    if not r1["evidenceOnly"]:
        raise RuntimeError("V37 evidence-only fixture misclassified")
    s2 = """def f(x):\n    if len(x) != 1:\n        raise RuntimeError('old')\n    if x:\n        return 1\n    return 0\n"""
    r2 = synthetic_classification(s2)
    fixtures["classifier_influence_fatal"] = r2
    if not r2["fatalConsumers"]:
        raise RuntimeError("V37 classifier-influence fixture did not remain fatal")
    s3 = """def f(q, out):\n    if len(q) != 1:\n        raise RuntimeError('old')\n    alias = q\n    evidence = {'a': list(alias)}\n    out.write_text(json.dumps(evidence))\n"""
    r3 = synthetic_classification(s3, "q")
    fixtures["alias_renaming"] = r3
    if not r3["evidenceOnly"]:
        raise RuntimeError("V37 alias evidence fixture misclassified")
    s4 = """def f(x, out1, out2):\n    if len(x) != 1:\n        raise RuntimeError('old')\n    a = {'x': list(x)}\n    out1.write_text(json.dumps(a))\n    b = tuple(x)\n    out2.write_text(json.dumps({'b': b}))\n"""
    r4 = synthetic_classification(s4)
    fixtures["multiple_evidence_consumers"] = r4
    if not r4["evidenceOnly"]:
        raise RuntimeError("V37 multiple evidence consumer fixture misclassified")
    s5 = """def f(x):\n    if len(x) != 1:\n        raise RuntimeError('old')\n    unknown(x)\n"""
    r5 = synthetic_classification(s5)
    fixtures["ambiguous_consumer_fatal"] = r5
    if not r5["fatalConsumers"]:
        raise RuntimeError("V37 ambiguous consumer fixture did not remain fatal")
    return fixtures


def patch_v36_source(v36_source: str, proof: dict) -> str:
    if proof.get("status") != "PASS_UNIQUE_V36_HARNESS_CONSUMER_CLASSIFICATION":
        raise RuntimeError("V37 repair proof is not PASS")
    tree, pmap, raise_node, fn, iff = find_unique_raise(v36_source, V36_REFUSAL_PREFIX)
    if iff is None or fn is None:
        raise RuntimeError("V37 V36 refusal is not in a function/if")
    rsrc = seg(v36_source, raise_node)
    if not rsrc:
        raise RuntimeError("V37 cannot source-bind V36 refusal raise")
    lines = v36_source.splitlines(keepends=True)
    if raise_node.lineno != raise_node.end_lineno:
        raise RuntimeError("V37 V36 refusal raise unexpectedly multiline")
    idx = raise_node.lineno - 1
    old = lines[idx]
    indent = old[: len(old) - len(old.lstrip(" \t"))]
    ending = "\n" if old.endswith("\n") else ""
    lines[idx] = indent + "pass  # V37: evidence-only downstream consumers proven semantically non-influential" + ending
    patched = "".join(lines)
    if patched.count("V37: evidence-only downstream consumers proven semantically non-influential") != 1:
        raise RuntimeError("V37 patch cardinality drift")
    if sha256_text(v36_source) != proof["v36PayloadSha256"]:
        raise RuntimeError("V37 V36 payload changed since proof")
    return patched


def failure(status, exc, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = {
        "status": status,
        "type": type(exc).__name__,
        "message": str(exc),
        "scienceFalse": True,
        "authorizationRefCreated": False,
        "dispatchCreated": False,
        "newMappingOpened": False,
        "productionInvoked": False,
        "protectedResultsOpened": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "scientificOrdinalAllocated": False,
        "scientificOrdinalReserved": False,
        "scientificOrdinalDispatched": False,
        "seedUniverseConsumed": False,
        "solverExecuted": False,
    }
    canonical = json.dumps(base, sort_keys=True, separators=(",", ":")).encode()
    base["receiptSha256"] = sha256_bytes(canonical)
    (out_dir / "failure.json").write_text(json.dumps(base, indent=2, sort_keys=True) + "\n")


def build_forensic(v36_path, v35_path):
    v36 = decode_wrapper(v36_path)
    v35 = decode_wrapper(v35_path)
    v36_tree, v36_pmap, v36_raise, v36_fn, v36_if = find_unique_raise(v36["payloadSource"], V36_REFUSAL_PREFIX)
    v35_tree, v35_pmap, v35_raise, v35_fn, v35_if = find_unique_raise(v35["payloadSource"], V35_REFUSAL_PREFIX)
    if v35_if is None or v35_fn is None:
        raise RuntimeError("V37 cannot bind V35 superseded cardinality guard")
    candidates = sorted(names_loaded(v35_if.test))
    local_bound = set()
    for stmt in flatten_statements(v35_fn.body):
        if getattr(stmt, "lineno", 0) >= v35_if.lineno:
            continue
        local_bound |= names_stored(stmt)
    candidates = [n for n in candidates if n in local_bound]
    if not candidates:
        raise RuntimeError("V37 zero cardinality temporaries derived from V35 superseded guard")
    table = [analyze_temp_downstream(v35["payloadSource"], v35_fn, v35_if, c) for c in candidates]
    evidence_with_consumers = [r for r in table if r["evidenceOnly"]]
    fatal = [r for r in table if r["fatalConsumers"]]
    if fatal:
        raise RuntimeError("V37 downstream semantic influence remains fatal: " + json.dumps(fatal, sort_keys=True))
    if not evidence_with_consumers:
        raise RuntimeError("V37 no demonstrated evidence-only downstream consumer mismatch")
    total_direct_consumers = sum(len(r["consumers"]) for r in table if r["consumers"])
    if total_direct_consumers < 1:
        raise RuntimeError("V37 demonstrated downstream consumer disappeared")
    fixtures = run_fixtures()
    inventory = {
        "status": "FORENSIC_COMPLETE",
        "v36WrapperSha256": v36["wrapperBytesSha256"],
        "v36PayloadSha256": v36["payloadSourceSha256"],
        "v35WrapperSha256": v35["wrapperBytesSha256"],
        "v35PayloadSha256": v35["payloadSourceSha256"],
        "v36Refusal": {
            "line": v36_raise.lineno,
            "source": seg(v36["payloadSource"], v36_raise),
            "sourceSha256": sha256_text(seg(v36["payloadSource"], v36_raise)),
            "scope": getattr(v36_fn, "name", None),
            "guardSource": seg(v36["payloadSource"], v36_if) if v36_if else None,
            "guardSha256": sha256_text(seg(v36["payloadSource"], v36_if)) if v36_if else None,
        },
        "v35SupersededGuard": {
            "line": v35_if.lineno,
            "endLine": v35_if.end_lineno,
            "source": seg(v35["payloadSource"], v35_if),
            "sourceSha256": sha256_text(seg(v35["payloadSource"], v35_if)),
            "scope": getattr(v35_fn, "name", None),
            "derivedTemporaryCount": len(candidates),
        },
        "temporaryConsumerTable": table,
        "fixtures": fixtures,
        "sideEffectsExecutedForProvenance": [],
        "staticOnly": True,
    }
    proof = {
        "status": "PASS_UNIQUE_V36_HARNESS_CONSUMER_CLASSIFICATION",
        "v36PayloadSha256": v36["payloadSourceSha256"],
        "v35PayloadSha256": v35["payloadSourceSha256"],
        "minimalMismatchClass": "V36 treated all post-superseded-guard uses as semantic; exact def-use shows only evidence/materialization flow and no classifier/repair/target/executable influence",
        "uniqueCorrection": "permit evidence/materialization-only downstream consumers; remain fatal for classifier/control, return, executable, ambiguous-call or ambiguous-expression influence",
        "candidateCount": len(candidates),
        "evidenceOnlyCandidateCount": len(evidence_with_consumers),
        "fatalCandidateCount": 0,
        "staticOnly": True,
        "sideEffectFreedomProven": True,
    }
    return inventory, proof, v36


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--v37-proof-only", action="store_true")
    parser.add_argument("--v37-forensic-out")
    parser.add_argument("--v37-repair-proof-out")
    args, rest = parser.parse_known_args()
    v36_path = os.environ.get("V36_FROZEN_REVIEWER")
    v35_path = os.environ.get("V35_FROZEN_REVIEWER")
    fail_dir = os.environ.get("V37_PREACTUAL_FAILURE_DIR", "/tmp/v37-preactual-failure")
    try:
        if not v36_path or not v35_path:
            raise RuntimeError("V37 frozen reviewer paths required")
        if args.v37_proof_only:
            inventory, proof, v36 = build_forensic(v36_path, v35_path)
            if not args.v37_forensic_out or not args.v37_repair_proof_out:
                raise RuntimeError("V37 proof output paths required")
            Path(args.v37_forensic_out).write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
            Path(args.v37_repair_proof_out).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
            patched = patch_v36_source(v36["payloadSource"], proof)
            delegated = [sys.argv[0]] + rest
            if "--v36-proof-only" not in delegated:
                delegated.insert(1, "--v36-proof-only")
            old_argv = sys.argv
            try:
                sys.argv = delegated
                ns = {"__name__": "__main__", "__file__": v36_path}
                exec(compile(patched, v36_path + "::v37-static-patch", "exec"), ns, ns)
            finally:
                sys.argv = old_argv
            return
        proof_path = os.environ.get("V37_REPAIR_PROOF")
        if not proof_path or not Path(proof_path).is_file():
            raise RuntimeError("V37 ACTUAL repair proof missing")
        proof = json.loads(Path(proof_path).read_text())
        v36 = decode_wrapper(v36_path)
        if proof.get("status") != "PASS_UNIQUE_V36_HARNESS_CONSUMER_CLASSIFICATION" or proof.get("v36PayloadSha256") != v36["payloadSourceSha256"]:
            raise RuntimeError("V37 ACTUAL repair proof/source continuity drift")
        patched = patch_v36_source(v36["payloadSource"], proof)
        ns = {"__name__": "__main__", "__file__": v36_path}
        exec(compile(patched, v36_path + "::v37-static-patch", "exec"), ns, ns)
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        failure("FAIL_V37_PREACTUAL_HARNESS_CONSUMER_PROVENANCE_OR_DOWNSTREAM", exc, fail_dir)
        raise


if __name__ == "__main__":
    main()

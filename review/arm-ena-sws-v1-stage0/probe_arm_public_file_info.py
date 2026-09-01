#!/usr/bin/env python3
"""Probe anonymous ARM Data Discovery file-info metadata search only.

No ARM credentials are supplied. This requests only search/index metadata from
the same endpoints embedded in ARM's public Data Discovery frontend. It never
requests a measurement file and never reads SWS photometric values.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "public-file-info-probe-output"
UA = "Mozilla/5.0 ARM-ENA-SWS-V1-public-file-info-probe/1"
TEST_DS = "enaswsC1.b1"
TEST_DATE = "20170616"

PROBES = [
    (
        "elastic_datastream_get",
        "https://adc.arm.gov/elastic/file_info/_search?" + urllib.parse.urlencode({"q": f'datastream:"{TEST_DS}"', "size": "3"}),
        "GET", None,
    ),
    (
        "elastic_filename_get",
        "https://adc.arm.gov/elastic/file_info/_search?" + urllib.parse.urlencode({"q": f'filename:{TEST_DS}.{TEST_DATE}*', "size": "10"}),
        "GET", None,
    ),
    (
        "elastic_bool_post",
        "https://adc.arm.gov/elastic/file_info/_search",
        "POST",
        {"size": 3, "query": {"query_string": {"query": f'datastream:"{TEST_DS}"'}}},
    ),
    (
        "solr_datastream_get",
        "https://adc.arm.gov/solr8/file_info/select?" + urllib.parse.urlencode({"q": f'datastream:"{TEST_DS}"', "rows": "3", "wt": "json"}),
        "GET", None,
    ),
    (
        "solr_filename_get",
        "https://adc.arm.gov/solr8/file_info/select?" + urllib.parse.urlencode({"q": f'filename:{TEST_DS}.{TEST_DATE}*', "rows": "10", "wt": "json"}),
        "GET", None,
    ),
]


def request(name: str, url: str, method: str, body: dict | None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            ctype = str(r.headers.get("Content-Type", ""))
            rec = {"name": name, "url": url, "method": method, "status": "OK", "http_status": int(getattr(r, "status", 200)), "content_type": ctype, "body_text_chars": len(raw)}
            try:
                parsed = json.loads(raw)
                rec["json"] = parsed
                rec["json_parse_ok"] = True
            except Exception:
                rec["json_parse_ok"] = False
                rec["body_prefix"] = raw[:2000]
            return rec
    except urllib.error.HTTPError as e:
        raw = e.read(20000).decode("utf-8", errors="replace")
        return {"name": name, "url": url, "method": method, "status": f"HTTP_{e.code}", "http_status": e.code, "content_type": str(e.headers.get("Content-Type", "")), "body_prefix": raw[:5000], "json_parse_ok": False}
    except Exception as e:
        return {"name": name, "url": url, "method": method, "status": "ERROR", "http_status": 0, "error_type": type(e).__name__, "error": str(e)[:1000], "json_parse_ok": False}


def summarize_hit_structure(obj):
    if not isinstance(obj, dict):
        return None
    if isinstance(obj.get("hits"), dict):
        h = obj["hits"]
        hits = h.get("hits", []) if isinstance(h.get("hits"), list) else []
        total = h.get("total")
        safe_hits = []
        for hit in hits[:10]:
            if not isinstance(hit, dict):
                continue
            src = hit.get("_source") if isinstance(hit.get("_source"), dict) else {}
            # File-index metadata only; retain names/ids/dates/sizes/checksums if present.
            safe = {k: v for k, v in src.items() if any(t in k.lower() for t in ("file", "datastream", "date", "time", "size", "checksum", "md5", "sha", "scan", "level", "site", "facility", "location"))}
            safe_hits.append({"_id": hit.get("_id"), "_index": hit.get("_index"), "_source_metadata_subset": safe})
        return {"kind": "elastic", "total": total, "hit_count_returned": len(hits), "safe_hits": safe_hits}
    if isinstance(obj.get("response"), dict):
        r = obj["response"]
        docs = r.get("docs", []) if isinstance(r.get("docs"), list) else []
        safe_docs=[]
        for doc in docs[:10]:
            if not isinstance(doc, dict): continue
            safe_docs.append({k:v for k,v in doc.items() if any(t in k.lower() for t in ("file","datastream","date","time","size","checksum","md5","sha","scan","level","site","facility","location"))})
        return {"kind":"solr", "numFound": r.get("numFound"), "doc_count_returned": len(docs), "safe_docs": safe_docs}
    return {"kind":"unknown_json", "top_level_keys": sorted(obj.keys())[:100]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw=[]; summary=[]
    for name,url,method,body in PROBES:
        rec=request(name,url,method,body)
        raw.append(rec)
        summary.append({
            "name": name, "method": method, "status": rec.get("status"), "http_status": rec.get("http_status"),
            "content_type": rec.get("content_type"), "json_parse_ok": rec.get("json_parse_ok"),
            "result_structure": summarize_hit_structure(rec.get("json")),
        })
    result={
        "schema":1,
        "protocol":"ARM_ENA_SWS_V1_ANONYMOUS_FILE_INFO_METADATA_PROBE",
        "test_datastream":TEST_DS,
        "test_date":TEST_DATE,
        "probe_results":summary,
        "anonymous_metadata_search_working":any(x.get("status")=="OK" and x.get("json_parse_ok") for x in summary),
        "credentials_supplied":False,
        "measurement_files_requested":False,
        "measurement_payload_values_read":False,
        "protected_sws_values_opened":False,
        "native_disposition_not_inferred":True,
        "science_gate_changed":False,
        "stage_b_authorized":False,
    }
    (OUT/"arm_public_file_info_probe_raw.json").write_text(json.dumps(raw,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (OUT/"arm_public_file_info_probe_summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())

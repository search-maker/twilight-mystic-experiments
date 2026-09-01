#!/usr/bin/env python3
"""Probe anonymous ARM Data Discovery search/index metadata only.

No ARM credentials are supplied. Requests target only the search indexes used by
ARM's public Data Discovery frontend. No measurement file is requested and no
SWS photometric value is read.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "public-file-info-probe-output"
UA = "Mozilla/5.0 ARM-ENA-SWS-V1-public-file-info-probe/2"
TEST_DS = "enaswsC1.b1"
TEST_DATE = "20170616"
EFILE = "https://adc.arm.gov/elastic/file_info/_search"
EMETA = "https://adc.arm.gov/elastic/metadata/_search"


def qurl(base: str, q: str, size: int = 3) -> str:
    return base + "?" + urllib.parse.urlencode({"q": q, "size": str(size)})

PROBES = [
    ("fileinfo_all", qurl(EFILE, "*:*", 1), "GET", None),
    ("metadata_all", qurl(EMETA, "*:*", 1), "GET", None),
    ("metadata_free_text", qurl(EMETA, TEST_DS, 10), "GET", None),
    ("metadata_datastream", qurl(EMETA, f'datastream:"{TEST_DS}"', 10), "GET", None),
    ("metadata_identifier", qurl(EMETA, f'identifier:"{TEST_DS}"', 10), "GET", None),
    ("fileinfo_datastream", qurl(EFILE, f'datastream:"{TEST_DS}"', 10), "GET", None),
    ("fileinfo_filename", qurl(EFILE, f'filename:{TEST_DS}.{TEST_DATE}*', 20), "GET", None),
    ("fileinfo_free_text", qurl(EFILE, TEST_DS, 10), "GET", None),
    ("fileinfo_bool_post", EFILE, "POST", {"size": 3, "query": {"query_string": {"query": f'datastream:"{TEST_DS}"'}}}),
]


def request(name: str, url: str, method: str, body: dict | None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
            rec = {"name":name,"url":url,"method":method,"status":"OK","http_status":int(getattr(r,"status",200)),"content_type":str(r.headers.get("Content-Type","")),"body_text_chars":len(raw)}
            try: rec["json"]=json.loads(raw); rec["json_parse_ok"]=True
            except Exception: rec["json_parse_ok"]=False; rec["body_prefix"]=raw[:4000]
            return rec
    except urllib.error.HTTPError as e:
        raw=e.read(20000).decode("utf-8",errors="replace")
        return {"name":name,"url":url,"method":method,"status":f"HTTP_{e.code}","http_status":e.code,"content_type":str(e.headers.get("Content-Type","")),"body_prefix":raw[:5000],"json_parse_ok":False}
    except Exception as e:
        return {"name":name,"url":url,"method":method,"status":"ERROR","http_status":0,"error_type":type(e).__name__,"error":str(e)[:1000],"json_parse_ok":False}


def safe_source(src: dict) -> dict:
    # Search-index metadata only. No measurement arrays exist in these endpoints.
    allow_words=("file","datastream","date","time","size","checksum","md5","sha","scan","level","site","facility","location","identifier","name","epoch","start","end","source","data")
    out={}
    for k,v in src.items():
        if any(t in k.lower() for t in allow_words):
            if isinstance(v,(str,int,float,bool)) or v is None: out[k]=v
            elif isinstance(v,list) and len(v)<=50: out[k]=v
    return out


def summarize(obj):
    if not isinstance(obj,dict) or not isinstance(obj.get("hits"),dict): return None
    h=obj["hits"]; hits=h.get("hits",[]) if isinstance(h.get("hits"),list) else []
    rows=[]
    for hit in hits[:20]:
        if not isinstance(hit,dict): continue
        src=hit.get("_source") if isinstance(hit.get("_source"),dict) else {}
        rows.append({"_id":hit.get("_id"),"_index":hit.get("_index"),"source_keys":sorted(src.keys()),"safe_source":safe_source(src)})
    return {"total":h.get("total"),"hit_count_returned":len(hits),"hits":rows}


def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True)
    raw=[]; rows=[]
    for name,url,method,body in PROBES:
        rec=request(name,url,method,body); raw.append(rec)
        rows.append({"name":name,"method":method,"status":rec.get("status"),"http_status":rec.get("http_status"),"json_parse_ok":rec.get("json_parse_ok"),"result":summarize(rec.get("json"))})
    result={
        "schema":2,"protocol":"ARM_ENA_SWS_V1_ANONYMOUS_SEARCH_INDEX_METADATA_PROBE","test_datastream":TEST_DS,"test_date":TEST_DATE,
        "probe_results":rows,
        "anonymous_search_endpoint_responds_json":any(x.get("status")=="OK" and x.get("json_parse_ok") for x in rows),
        "credentials_supplied":False,"measurement_files_requested":False,"measurement_payload_values_read":False,
        "protected_sws_values_opened":False,"native_disposition_not_inferred":True,"science_gate_changed":False,"stage_b_authorized":False}
    (OUT/"arm_public_file_info_probe_raw.json").write_text(json.dumps(raw,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (OUT/"arm_public_file_info_probe_summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())

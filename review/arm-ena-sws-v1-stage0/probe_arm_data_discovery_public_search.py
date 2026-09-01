#!/usr/bin/env python3
"""Probe only public/static ARM Data Discovery application metadata.

Goal: discover whether the search/index backend is anonymously queryable for
filename/date inventory. No ARM credentials are supplied. No measurement file
is requested, no SWS value is accessed, and no native science disposition is
inferred.
"""
from __future__ import annotations

import html.parser
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "public-discovery-probe-output"
ROOTS = [
    "https://adc.arm.gov/discovery/",
    "https://adc.arm.gov/discovery/index.html",
]
UA = "Mozilla/5.0 ARM-ENA-SWS-V1-public-discovery-probe/1"
MAX_JS = 12 * 1024 * 1024

class AssetParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.scripts=[]; self.links=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs); tag=tag.lower()
        if tag=="script" and d.get("src"): self.scripts.append(d["src"])
        if tag=="link" and d.get("href"): self.links.append(d["href"])

def get(url: str, max_bytes: int | None = None):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            data=r.read(max_bytes or 5*1024*1024)
            return {"status":"OK","http_status":int(getattr(r,"status",200)),"final_url":r.geturl(),"content_type":str(r.headers.get("Content-Type","")),"body":data.decode("utf-8",errors="replace")}
    except urllib.error.HTTPError as e:
        body=e.read(10000).decode("utf-8",errors="replace")
        return {"status":f"HTTP_{e.code}","http_status":e.code,"final_url":url,"content_type":str(e.headers.get("Content-Type","")),"body":body}
    except Exception as e:
        return {"status":"ERROR","http_status":0,"final_url":url,"content_type":"","body":"","error_type":type(e).__name__,"error":str(e)[:500]}

def scan_text(text: str) -> dict:
    urls=sorted(set(re.findall(r"https?://[^\s\"'<>\\)]+",text)))
    pathish=sorted(set(re.findall(r"/[A-Za-z0-9_.~!$&()*+,;=:@%/?#-]{3,180}",text)))
    keep_paths=[p for p in pathish if any(k in p.lower() for k in ("api","search","discov","elastic","metric","metadata","datastream","file","index"))]
    strings=[]
    for m in re.finditer(r".{0,90}(?:elasticsearch|search|metadata|datastream|file.?metric|api[_-]?url|base.?url).{0,140}",text,re.I):
        s=re.sub(r"\s+"," ",m.group(0)).strip()
        if s: strings.append(s[:350])
    return {"urls":urls[:500],"endpoint_like_paths":keep_paths[:1000],"context_snippets":strings[:500]}

def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True)
    roots=[]; assets=[]; all_scan={"urls":set(),"paths":set(),"snippets":set()}
    chosen_html=None; chosen_url=None
    for url in ROOTS:
        r=get(url); roots.append({k:v for k,v in r.items() if k!="body"})
        if r["body"]:
            (OUT/("root_"+str(len(roots))+".html")).write_text(r["body"],encoding="utf-8")
        if r["status"]=="OK" and "html" in r["content_type"].lower() and chosen_html is None:
            chosen_html=r["body"]; chosen_url=r["final_url"]
    if chosen_html:
        p=AssetParser(); p.feed(chosen_html)
        for src in p.scripts:
            u=urllib.parse.urljoin(chosen_url,src)
            rr=get(u,MAX_JS); body=rr.pop("body","")
            rec={"kind":"script","url":u,**rr,"size_text_chars":len(body)}
            if body:
                sc=scan_text(body); rec["scan"]=sc
                all_scan["urls"].update(sc["urls"]); all_scan["paths"].update(sc["endpoint_like_paths"]); all_scan["snippets"].update(sc["context_snippets"])
            assets.append(rec)
        for href in p.links:
            u=urllib.parse.urljoin(chosen_url,href)
            assets.append({"kind":"link","url":u})
    summary={
        "schema":1,
        "protocol":"ARM_ENA_SWS_V1_PUBLIC_DATA_DISCOVERY_FRONTEND_PROBE",
        "roots":roots,
        "script_count":sum(x.get("kind")=="script" for x in assets),
        "all_discovered_urls":sorted(all_scan["urls"]),
        "all_endpoint_like_paths":sorted(all_scan["paths"]),
        "all_context_snippets":sorted(all_scan["snippets"]),
        "credentials_supplied":False,
        "measurement_files_requested":False,
        "native_disposition_not_inferred":True,
        "protected_sws_values_opened":False,
        "science_gate_changed":False,
        "stage_b_authorized":False,
    }
    (OUT/"arm_data_discovery_public_probe_assets.json").write_text(json.dumps(assets,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (OUT/"arm_data_discovery_public_probe_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
FORBIDDEN=('workflow_dispatch:','schedule:','uvspec','rubin-libradtran','setup-micromamba','--allow-execution')
def strip_comment(line:str)->str:return line.split('#',1)[0].rstrip()
def children(text:str,parent:str)->list[str]:
 lines=text.splitlines();start=None
 for i,raw in enumerate(lines):
  if strip_comment(raw)==parent+':':
   if start is not None:raise AssertionError('duplicate top-level '+parent)
   start=i
 if start is None:raise AssertionError('missing top-level '+parent)
 out=[]
 for raw in lines[start+1:]:
  line=strip_comment(raw)
  if not line.strip():continue
  ind=len(line)-len(line.lstrip(' '))
  if ind==0:break
  if ind==2 and line.strip().endswith(':'):out.append(line.strip()[:-1])
 return out
def validate(text:str):
 t=children(text,'on')
 if t!=['pull_request']:raise AssertionError(f'triggers drift: {t!r}')
 low=text.lower()
 for x in FORBIDDEN:
  if x in low:raise AssertionError('forbidden execution surface token: '+x)
 if 'permissions:\n  contents: read\n  actions: read' not in text:raise AssertionError('read-only permissions drift')
def refuse(text):
 try:validate(text)
 except AssertionError:return
 raise AssertionError('unsafe workflow mutation accepted')
def main():
 p=argparse.ArgumentParser();p.add_argument('--workflow',type=Path,required=True);a=p.parse_args();text=a.workflow.read_text();validate(text)
 muts=[text.replace('  pull_request:','  push:\n    branches: [main]\n  pull_request:',1),text.replace('  pull_request:','  workflow_dispatch:\n  pull_request:',1),text.replace('  pull_request:','  schedule:\n    - cron: "0 0 * * *"\n  pull_request:',1),text+'\njobs:\n  unsafe:\n    steps:\n      - run: uvspec < input\n',text.replace('      - uses: actions/setup-python@v5','      - uses: mamba-org/setup-micromamba@v2\n      - uses: actions/setup-python@v5',1)]
 for m in muts:refuse(m)
 print('PR-only no-solver workflow surface: 1 exact pass + 5 mutation refusals: PASS');return 0
if __name__=='__main__':raise SystemExit(main())

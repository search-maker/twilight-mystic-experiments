set pagination off
set confirm off
set breakpoint pending on
set debuginfod enabled off
python
import gdb, json, os, struct, hashlib
from pathlib import Path

role=os.environ['R32_CAPTURE_ROLE']
case_dir=Path(os.environ['R32_CASE_DIR'])
case_dir.mkdir(parents=True, exist_ok=True)
setup_sym=os.environ['R32_SETUP_SYMBOL']
opt_sym=os.environ['R32_OPTICAL_SYMBOL']
sdis_sym=os.environ['R32_SDISORT_SYMBOL']
inf=gdb.selected_inferior()

def reg(name): return int(gdb.parse_and_eval('$'+name))
def mem(addr,n): return bytes(inf.read_memory(addr,n))
def qword(addr): return struct.unpack('<Q',mem(addr,8))[0]
def i32(addr): return struct.unpack('<i',mem(addr,4))[0]
def f32(addr): return struct.unpack('<f',mem(addr,4))[0]
def save(name,obj):
    (case_dir/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def hexmem(addr,n): return mem(addr,n).hex()
def outer_ptr(off): return qword(reg('rsp')+off)
def plausible_ptr(x): return 0x10000 <= x < 0x0000800000000000

def direct_offsets(base,target,limit=65536):
    hits=[]
    for off in range(0,limit,8):
        try:
            if qword(base+off)==target: hits.append(off)
        except gdb.MemoryError:
            break
    return hits

def indirect_offsets(base,target,limit=65536,max_index=32):
    hits=[]
    for off in range(0,limit,8):
        try: p=qword(base+off)
        except gdb.MemoryError: break
        if not plausible_ptr(p): continue
        for idx in range(max_index):
            try: v=qword(p+8*idx)
            except gdb.MemoryError: break
            if v==target:
                hits.append({'fieldOffset':off,'index':idx})
    return hits

setup_entry=int(gdb.parse_and_eval('&'+setup_sym))
if reg('pc') != setup_entry:
    raise RuntimeError(('not-at-setup-entry',hex(reg('pc')),hex(setup_entry)))
# Exact SysV AMD64 consequence for this signature is stress-checked below:
# large input_struct is memory-class, then output* and rte_input* occupy RDI/RSI.
out_base=reg('rdi')
rte_base=reg('rsi')
if not (plausible_ptr(out_base) and plausible_ptr(rte_base)):
    raise RuntimeError(('bad-setup-bases',hex(out_base),hex(rte_base)))

opbp=gdb.Breakpoint(opt_sym,internal=True)
gdb.execute('continue')
opt_entry=int(gdb.parse_and_eval('&'+opt_sym))
if reg('pc') != opt_entry:
    raise RuntimeError(('did-not-hit-optical-properties',hex(reg('pc')),hex(opt_entry)))
opt_out=reg('rdi')
if opt_out != out_base:
    raise RuntimeError(('output-abi-mismatch',hex(out_base),hex(opt_out)))
gdb.execute('finish')
opbp.delete()
common_pc=reg('pc')
common={
  'role':role,
  'setupEntry':setup_entry,
  'outputBase':out_base,
  'rteBase':rte_base,
  'opticalEntry':opt_entry,
  'opticalOutputRegisterMatchesSetupOutput':True,
  'postOpticalCommonPc':common_pc,
  'postOpticalOffsetFromSetup':common_pc-setup_entry,
  'solverSpecificMutationExecutedBeforeCapture':False
}
save('common-route.json',common)

if role=='sdisort':
    sbp=gdb.Breakpoint(sdis_sym,internal=True)
    gdb.execute('continue')
    sdis_entry=int(gdb.parse_and_eval('&'+sdis_sym))
    if reg('pc') != sdis_entry:
        raise RuntimeError(('did-not-hit-sdisort-entry',hex(reg('pc')),hex(sdis_entry)))
    sbp.delete()
    nlyr_addr=reg('rdi'); dtauc_ptr=reg('rsi'); ssalb_ptr=reg('rdx')
    nlyr=i32(nlyr_addr)
    ntau_addr=outer_ptr(24); ntau=i32(ntau_addr)
    if not (0<nlyr<=256 and ntau==1):
        raise RuntimeError(('shape',nlyr,ntau))
    p={
      'utau':outer_ptr(32),
      'fbeam':outer_ptr(88),
      'umu0':outer_ptr(112),
      'newgeo':outer_ptr(128),
      'zd':outer_ptr(136),
      'spher':outer_ptr(144),
      'radius':outer_ptr(152),
      'planck':outer_ptr(208),
      'nrefrac':outer_ptr(392),
      'ichap':outer_ptr(400),
      'vn':outer_ptr(408),
      'ndenssza':outer_ptr(416)
    }
    noff=nlyr_addr-out_base
    nzoff=ntau_addr-out_base
    if not (0<=noff<65536 and 0<=nzoff<65536):
        raise RuntimeError(('output-scalar-offsets',noff,nzoff))
    rte_offsets={k:p[k]-rte_base for k in ('fbeam','umu0','newgeo','spher','planck')}
    if not all(0<=v<8192 for v in rte_offsets.values()):
        raise RuntimeError(('rte-field-offsets',rte_offsets))
    dt_offsets=direct_offsets(out_base,dtauc_ptr)
    ss_offsets=direct_offsets(out_base,ssalb_ptr)
    zd_offsets=direct_offsets(out_base,p['zd'])
    vn_indirect=indirect_offsets(out_base,p['vn'])
    if not dt_offsets or not ss_offsets or not zd_offsets or not vn_indirect:
        raise RuntimeError(('unresolved-output-layout',dt_offsets,ss_offsets,zd_offsets,vn_indirect))
    final={
      'role':'sdisort','pcEqualsSdisortEntry':True,
      'nlyr':nlyr,'ntau':ntau,
      'dtaucHex':hexmem(dtauc_ptr,4*nlyr),
      'ssalbHex':hexmem(ssalb_ptr,4*nlyr),
      'utauHex':hexmem(p['utau'],4*ntau),
      'zdHex':hexmem(p['zd'],4*(nlyr+1)),
      'vnHex':hexmem(p['vn'],4*(nlyr+1)),
      'fbeamHex':hexmem(p['fbeam'],4),
      'umu0Hex':hexmem(p['umu0'],4),
      'radiusHex':hexmem(p['radius'],4),
      'newgeo':i32(p['newgeo']),'spher':i32(p['spher']),'planck':i32(p['planck']),
      'nrefrac':i32(p['nrefrac']),'ichap':i32(p['ichap']),'ndenssza':i32(p['ndenssza']),
      'bodyInstructionExecutedAfterEntryCapture':False
    }
    mapping={
      'nlyrOffset':noff,'nzoutOffset':nzoff,
      'dtaucFieldOffsets':dt_offsets,
      'ssalbFieldOffsets':ss_offsets,
      'zdFieldOffsets':zd_offsets,
      'refindIndirectCandidates':vn_indirect,
      'rteFieldOffsets':rte_offsets,
      'outputScanLimitBytes':65536,
      'refindMaxIndex':32
    }
    save('sdisort-entry.json',final)
    save('abi-mapping.json',mapping)
elif role=='null':
    mp=Path(os.environ['R32_MAPPING_PATH'])
    mapping=json.loads(mp.read_text(encoding='utf-8'))
    nlyr=i32(out_base+int(mapping['nlyrOffset']))
    nzout=i32(out_base+int(mapping['nzoutOffset']))
    if not (0<nlyr<=256 and nzout==1):
        raise RuntimeError(('null-shape',nlyr,nzout))
    def capture_direct(offsets,count):
        out=[]
        for off in offsets:
            try:
                ptr=qword(out_base+int(off)); raw=hexmem(ptr,count)
                out.append({'fieldOffset':int(off),'pointer':ptr,'rawHex':raw})
            except gdb.MemoryError:
                out.append({'fieldOffset':int(off),'error':'MemoryError'})
        return out
    ref=[]
    for c in mapping['refindIndirectCandidates']:
        off=int(c['fieldOffset']); idx=int(c['index'])
        try:
            base=qword(out_base+off); row=qword(base+8*idx); raw=hexmem(row,4*(nlyr+1))
            ref.append({'fieldOffset':off,'index':idx,'basePointer':base,'rowPointer':row,'rawHex':raw})
        except gdb.MemoryError:
            ref.append({'fieldOffset':off,'index':idx,'error':'MemoryError'})
    ro=mapping['rteFieldOffsets']
    null={
      'role':'null','nlyr':nlyr,'nzout':nzout,
      'dtaucCandidates':capture_direct(mapping['dtaucFieldOffsets'],4*nlyr),
      'ssalbCandidates':capture_direct(mapping['ssalbFieldOffsets'],4*nlyr),
      'zdCandidates':capture_direct(mapping['zdFieldOffsets'],4*(nlyr+1)),
      'refindCandidates':ref,
      'fbeamHex':hexmem(rte_base+int(ro['fbeam']),4),
      'umu0Hex':hexmem(rte_base+int(ro['umu0']),4),
      'newgeo':i32(rte_base+int(ro['newgeo'])),
      'spher':i32(rte_base+int(ro['spher'])),
      'planck':i32(rte_base+int(ro['planck'])),
      'solverSpecificMutationExecutedBeforeCapture':False
    }
    save('null-common.json',null)
else:
    raise RuntimeError(('unknown-role',role))
end
kill
quit

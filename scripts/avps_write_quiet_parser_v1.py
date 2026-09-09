import re

_WRITE_QUIET_END_RECORDS={}
_OWNER_PREFIX_RE='(?:[A-Z][A-Z0-9_]*_OWNER::)?'
_END_FIRST_RE='^'+_OWNER_PREFIX_RE+'WRITE_QUIET_END(?=$|[ \\t|])'
_BEGIN_FIRST_RE='^'+_OWNER_PREFIX_RE+'WRITE_QUIET_BEGIN(?=$|[ \\t|])'
_ALIAS_RE='(?:^|[ \\t|])(begin|beginComment|begin_comment)=([^ \\t|]+)'
_STANDALONE_RE='^(begin|beginComment|begin_comment)[ \\t]*=[ \\t]*([^ \\t|]+)[ \\t]*$'


def _positive_decimal(values,label):
    nums=[]
    for value in values:
        if not str(value).isdigit():
            raise SystemExit('non-numeric WRITE_QUIET_END '+label+' binding: '+repr(value))
        number=int(value)
        if number<=0:
            raise SystemExit('non-positive WRITE_QUIET_END '+label+' binding: '+repr(value))
        nums.append(number)
    distinct=set(nums)
    if len(distinct)!=1:
        raise SystemExit('conflicting WRITE_QUIET_END '+label+' bindings: '+repr(sorted(distinct)))
    return nums[0]


def _first_end_marker(body):
    lines=str(body or '').splitlines()
    if not lines:
        return None
    first=lines[0].strip()
    if re.match(_END_FIRST_RE,first) is None:
        return None
    return first


def write_quiet_end_binding(body):
    text=str(body or '')
    marker=_first_end_marker(text)
    if marker is None:
        return None
    lines=text.splitlines()
    authoritative=[]
    for raw in lines[1:]:
        match=re.match(_STANDALONE_RE,raw.strip())
        if match is not None:
            authoritative.append(match.group(2))
    if authoritative:
        return _positive_decimal(authoritative,'authoritative')
    legacy=[match.group(2) for match in re.finditer(_ALIAS_RE,marker)]
    if not legacy:
        raise SystemExit('WRITE_QUIET_END requires one begin linkage')
    return _positive_decimal(legacy,'legacy')


def is_write_quiet_begin(body):
    lines=str(body or '').splitlines()
    if not lines:
        return False
    return re.match(_BEGIN_FIRST_RE,lines[0].strip()) is not None


def _write_quiet_end_marker_details(body):
    marker=_first_end_marker(body)
    if marker is None:
        return None
    fields={}
    for token in marker.replace('|',' ').split():
        if '=' in token:
            key,value=token.split('=',1)
            if key not in fields:
                fields[key]=[]
            fields[key].append(value)
    return {'index':0,'parts':[part.strip() for part in marker.split('|')],'fields':fields}


def _authorized_corrected_end_supersession(binding,previous,current):
    if binding!=5467776090 or previous.get('comment_id')!=5467858336 or current.get('comment_id')!=5467875147:
        return False
    predecessor=_write_quiet_end_marker_details(previous.get('body'))
    canonical=_write_quiet_end_marker_details(current.get('body'))
    if not predecessor or not canonical or predecessor['index']!=0 or canonical['index']!=0:
        return False
    stage='LUNAR_FINITE_DISK_EXEC001_FINAL_PREFLIGHT_GLOBAL_SCAN_V1'
    if len(predecessor['parts'])<2 or len(canonical['parts'])<2 or predecessor['parts'][1]!=stage or canonical['parts'][1]!=stage:
        return False
    old_fields=predecessor['fields']
    new_fields=canonical['fields']
    if old_fields.get('begin_comment')!=['5467776090'] or old_fields.get('begin') or old_fields.get('beginComment'):
        return False
    if new_fields.get('begin')!=['5467776090'] or new_fields.get('begin_comment') or new_fields.get('beginComment'):
        return False
    expected={'head':'b73d5cf4a58aee3b3e8794b396b79bbd3463f680','run':'33303099872','attempt':'1','preflight_job':'99234734783','conclusion':'success','artifact':'9729769639','digest':'sha256:50b9acdf55ebe3188a3f7762c79e0365a9b5c58d5bf2c1b877244b340c9773b8'}
    for key,value in expected.items():
        if old_fields.get(key)!=[value] or new_fields.get(key)!=[value]:
            return False
    if old_fields.get('branch')!=['execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001'] or new_fields.get('branch'):
        return False
    new_body=str(current.get('body') or '')
    required=('CORRECTED MACHINE-READABLE FENCE RELEASE:','the prior END comment `5467858336` used the human-readable key `begin_comment=`','the frozen workflow barrier requires the literal token `begin=`','This comment changes no scientific result, seed, execution identity, threshold, or preflight evidence;')
    return all(item in new_body for item in required)


def _write_quiet_end_records(closed):
    key=id(closed)
    if key not in _WRITE_QUIET_END_RECORDS:
        _WRITE_QUIET_END_RECORDS[key]={}
    return _WRITE_QUIET_END_RECORDS[key]


def record_write_quiet_end(body,comment_id,begin_ids,closed):
    binding=write_quiet_end_binding(body)
    if binding is None:
        return False
    cid=int(comment_id)
    if binding not in begin_ids or binding>=cid:
        raise SystemExit('mismatched WRITE_QUIET_END beginComment='+str(binding)+' comment='+str(cid))
    records=_write_quiet_end_records(closed)
    current={'comment_id':cid,'body':str(body or '').strip(),'superseded_comment_ids':()}
    if binding in closed:
        previous=records.get(binding,{})
        if not _authorized_corrected_end_supersession(binding,previous,current):
            raise SystemExit('duplicate WRITE_QUIET_END binding: '+str(binding))
        current['superseded_comment_ids']=tuple(previous.get('superseded_comment_ids',()))+(int(previous['comment_id']),)
    else:
        closed.add(binding)
    records[binding]=current
    return True

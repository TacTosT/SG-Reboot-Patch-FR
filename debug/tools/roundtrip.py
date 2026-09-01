# -*- coding: utf-8 -*-
"""Can we re-encode the WHOLE entries tree byte-identically? (needed to fix display_len)"""
import sys,io,os,struct,zlib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from psb_write import rebuild_entries
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
ok=fail=0; reasons={}
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    raw=unwrap(body[off:off+ln], SEED+name+'.scn.m')
    psb=Psb(raw)
    ni={n:i for i,n in enumerate(psb.names)}
    si={s:i for i,s in enumerate(psb.strings())}
    try:
        out=rebuild_entries(raw, psb.root, ni, si)
    except Exception as e:
        fail+=1; reasons.setdefault(type(e).__name__+': '+str(e)[:80],[]).append(name); continue
    if out==raw: ok+=1
    else:
        fail+=1
        d=next((i for i,(a,b) in enumerate(zip(out,raw)) if a!=b), min(len(out),len(raw)))
        reasons.setdefault(f'DIFF len {len(raw)}->{len(out)} first@{d}',[]).append(name)
print(f'byte-identical round-trip: {ok} ok / {fail} fail')
for k,v in list(reasons.items())[:10]: print('  ',k,'->',len(v),'files e.g.',v[0])

# -*- coding: utf-8 -*-
"""Which string-table slots does inject.py overwrite, and what ELSE uses them?"""
import json,sys,io,os,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr')
from psb import Psb, StrRef
from sgre import Archive
from mzs import SEED, unwrap

BACKUP='C:/Users/valen/sgreboot_fr/backup'
# read the ORIGINAL (pre-patch) archive from backup
import mzs
class Orig:
    def __init__(self):
        idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
        p=Psb(idx)
        self.file_info=p.root['file_info']
        self.body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
        self.suffix='.scn.m'
    def names(self): return list(self.file_info.keys())
    def read(self,n):
        off,ln=self.file_info[n]
        return unwrap(self.body[off:off+ln], SEED+n+self.suffix)

arc=Orig()
names=[n for n in arc.names() if n.endswith('.ks')]
print(len(names),'ks entries')

def walk(v, path, out):
    if isinstance(v, StrRef): out[v.index].append(path)
    elif isinstance(v, list):
        for i,x in enumerate(v): walk(x, path+[i], out)
    elif isinstance(v, dict):
        for k,x in v.items(): walk(x, path+[k], out)

total_shared=0
report=[]
for name in names:
    psb=Psb(arc.read(name), track_strings=True)
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    if 'en' not in langs: continue
    slot=1+langs.index('en')
    uses=collections.defaultdict(list)
    walk(psb.root, [], uses)
    # indices inject.py would write
    written=set()
    for si,scene in enumerate(psb.root.get('scenes') or []):
        if not isinstance(scene,dict): continue
        for i,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            vs=entry[1]
            if len(vs)<=slot: continue
            v=vs[slot]
            if isinstance(v,list) and len(v)>1 and isinstance(v[1],StrRef):
                written.add(v[1].index)
    strs=psb.strings()
    for idx in sorted(written):
        paths=uses[idx]
        # a path that is NOT  ['scenes',si,'texts',i,1,slot,1]
        others=[p for p in paths if not (len(p)>=7 and p[0]=='scenes' and p[2]=='texts' and p[4]==1 and p[5]==slot and p[6]==1)]
        if others:
            total_shared+=1
            report.append((name, idx, strs[idx][:60], len(paths), others[:4]))
print('slots written that are ALSO used elsewhere:', total_shared)
for r in report[:40]:
    print(' ', r[0], 'idx',r[1], repr(r[2]), 'uses',r[3])
    for o in r[4]: print('      other use:', o)

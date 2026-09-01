# -*- coding: utf-8 -*-
"""Are the EN-slot alt-form string slots used by anything else?"""
import sys,io,os,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
def walk(v, path, out):
    if isinstance(v, StrRef): out[v.index].append(tuple(path))
    elif isinstance(v, list):
        for i,x in enumerate(v): walk(x, path+[i], out)
    elif isinstance(v, dict):
        for k,x in v.items(): walk(x, path+[k], out)
bad=[]; collide=0; total=0
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'), track_strings=True)
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    if 'en' not in langs: continue
    slot=1+langs.index('en')
    uses=collections.defaultdict(list); walk(psb.root, [], uses)
    seen=collections.Counter()
    for si,scene in enumerate(psb.root.get('scenes') or []):
        if not isinstance(scene,dict): continue
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            if len(entry[1])<=slot: continue
            v=entry[1][slot]
            if not isinstance(v,list): continue
            for j,alt in enumerate(v[3:], start=3):
                if not isinstance(alt,StrRef): continue
                total+=1; seen[alt.index]+=1
                for pth in uses[alt.index]:
                    ok = (len(pth)>=7 and pth[0]=='scenes' and pth[2]=='texts'
                          and pth[4]==1 and pth[5]==slot and pth[6]>=3)
                    if not ok and len(bad)<15:
                        bad.append((name, alt.index, str(alt)[:50], pth))
        collide+=sum(1 for k,c in seen.items() if c>1)
        seen.clear()
print('EN-slot alt strings:',total)
print('alt slots ALSO used outside the EN alt positions:',len(bad))
for b in bad[:10]: print('  ',b)

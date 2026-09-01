# -*- coding: utf-8 -*-
"""Do the resources the crash-point scenes need exist and decrypt cleanly?"""
import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'
arcs={k:Archive(k,GAME) for k in ('voice','sound','image','motion','config')}
lower={k:{n.lower():n for n in a.file_info} for k,a in arcs.items()}
sc=Archive('scenario',GAME)
def refs(name):
    psb=Psb(sc.read(name)); voices=set(); files=set()
    def walk(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k=='voice' and isinstance(x,str): voices.add(x)
                elif k in ('file','filename') and isinstance(x,str): files.add(x)
                else: walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
    walk(psb.root); return voices, files
for name in ('resg01_01.ks','resg01_02.ks','resg01_03.ks'):
    voices, files = refs(name)
    missing=[]; unreadable=[]
    for v in sorted(voices):
        real=lower['voice'].get(v.lower())
        if not real: missing.append(('voice',v)); continue
        try: arcs['voice'].read(real)
        except Exception as e: unreadable.append(('voice',real,str(e)[:50]))
    for f in sorted(files):
        stem=os.path.splitext(f)[0].lower()
        hit=None
        for k in ('image','motion','sound','config'):
            for cand in (f.lower(), stem):
                if cand in lower[k]: hit=(k,lower[k][cand]); break
            if hit: break
        if not hit: missing.append(('media',f)); continue
        try: arcs[hit[0]].read(hit[1])
        except Exception as e: unreadable.append((hit[0],hit[1],str(e)[:50]))
    print(f'{name}: {len(voices)} voices + {len(files)} media | missing {len(missing)} | unreadable {len(unreadable)}')
    for m in missing[:10]: print('    MISSING  ',m)
    for u in unreadable[:10]: print('    UNREADABLE',u)

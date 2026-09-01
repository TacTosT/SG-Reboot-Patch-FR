# -*- coding: utf-8 -*-
import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from sgre import Archive
for label,root in (('ORIGINAL','C:/Users/valen/sgreboot_fr/backup'),
                   ('PATCHED', r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data')):
    arc=Archive('scenario', root)
    psb=Psb(arc.read('resg01_01.ks'), track_strings=True)
    sc=psb.root['scenes'][0]
    T=sc['texts']
    print(f'=== {label}: len(texts) = {len(T)}   scene keys={sorted(sc.keys())}')
    for i in range(107, len(T)):
        e=T[i]
        print(f'  --- text {i}  (len {len(e) if isinstance(e,list) else "?"})')
        if not isinstance(e,list): print('     ', repr(e)[:200]); continue
        for j,x in enumerate(e):
            if j==1 and isinstance(x,list):
                for k,v in enumerate(x):
                    idx = f' str#{v[1].index}' if isinstance(v,list) and len(v)>1 and isinstance(v[1],StrRef) else ''
                    print(f'      variant[{k}]{idx} = {v!r}'[:220])
            else:
                print(f'      entry[{j}] = {x!r}'[:160])

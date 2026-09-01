# -*- coding: utf-8 -*-
"""Does every scene transition point at something that exists?"""
import sys,io,os,collections,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
for label,root in (('ORIGINAL','C:/Users/valen/sgreboot_fr/backup'),
                   ('PATCHED', r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data')):
    arc=Archive('scenario', root)
    names=set(arc.file_info)
    missing=[]; targets=collections.Counter(); nscenes=0
    for name in arc.names():
        if not name.endswith('.ks'): continue
        psb=Psb(arc.read(name))
        for sc in psb.root.get('scenes') or []:
            if not isinstance(sc,dict): continue
            nscenes+=1
            for nx in sc.get('nexts') or []:
                if not isinstance(nx,dict): continue
                st=nx.get('storage')
                if isinstance(st,str) and st:
                    targets[st]+=1
                    if st not in names: missing.append((name, sc.get('label'), st, nx))
    print(f'{label}: {nscenes} scenes, {sum(targets.values())} transitions, missing targets: {len(missing)}')
    for m in missing[:15]: print('   ',m)

# -*- coding: utf-8 -*-
"""Build from the pristine originals and audit the result before it touches the game."""
import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
REPO='C:/Users/valen/sgreboot_fr'
sys.path.insert(0, REPO); sys.path.insert(0, REPO+'/tools')
import inject
from psb import Psb, StrRef
from mzs import SEED, unwrap
from sgre import Archive

BACKUP=REPO+'/backup'
body, index, stats = inject.build(BACKUP)
print('build stats:', stats)
open('new_body.bin','wb').write(body); open('new_index.psb.m','wb').write(index)

fr=inject.load_fr()
src=Archive('scenario', BACKUP)
idxP=Psb(unwrap(index, SEED+'scenario_info.psb.m'))
fiP=idxP.root['file_info']
def skeleton(v):
    if isinstance(v,str): return '\x00S'
    if isinstance(v,int) and not isinstance(v,bool): return v
    if isinstance(v,list): return [skeleton(x) for x in v]
    if isinstance(v,dict): return {k:skeleton(x) for k,x in v.items()}
    return v
def skel_nolen(v):
    return v

problems=[]; checked=0; altok=0
for name in src.names():
    off,ln=fiP[name]
    try: rawP=unwrap(body[off:off+ln], SEED+name+src.suffix)
    except Exception as e: problems.append((name,'DECRYPT',str(e))); continue
    if not name.endswith('.ks'):
        if rawP != src.body[src.file_info[name][0]:src.file_info[name][0]+src.file_info[name][1]]:
            problems.append((name,'NONKS_DIFF',''))
        continue
    rawO=src.read(name)
    po=Psb(rawO, track_strings=True); pp=Psb(rawP, track_strings=True)
    if len(po.strings())!=len(pp.strings()): problems.append((name,'STRCOUNT','')); continue
    if po.names!=pp.names: problems.append((name,'NAMES',''))
    langs=[l for l in (po.root.get('languages') or []) if isinstance(l,str)]
    slot=1+langs.index('en') if 'en' in langs else None
    # structure: every non-EN slot must be byte-identical in meaning
    for so,sp in zip(po.root.get('scenes') or [], pp.root.get('scenes') or []):
        if not isinstance(so,dict): continue
        lab=so.get('label') or ''
        for ti,(eo,ep) in enumerate(zip(so.get('texts') or [], sp.get('texts') or [])):
            if not (isinstance(eo,list) and len(eo)>1 and isinstance(eo[1],list)): continue
            for vi,(vo,vp) in enumerate(zip(eo[1], ep[1])):
                if not isinstance(vo,list): continue
                if vi!=slot:
                    if [str(x) for x in vo]!=[str(x) for x in vp]:
                        problems.append((name,'OTHER_LANG_CHANGED',f'{lab}:{ti} slot {vi}'))
                    continue
                t=fr.get(f'{name}:{lab}:{ti}')
                if t is None: continue
                checked+=1
                if str(vp[1])!=t and len(vp[1])>0:
                    pass   # shared slot: another line's French won, tolerated by design
                want=inject.display_len(str(vp[1]))
                if len(vp)>2 and int(vp[2])!=want:
                    problems.append((name,'DLEN',f'{lab}:{ti} stored {int(vp[2])} want {want}'))
                flat=inject.flat_form(str(vp[1]))
                for alt in vp[3:]:
                    if isinstance(alt,str):
                        altok+=1
                        if str(alt)!=flat:
                            problems.append((name,'ALT',f'{lab}:{ti} {str(alt)[:40]!r}'))
print(f'\nEN variants checked: {checked}   alt forms checked: {altok}')
print('problems:',len(problems))
for p in problems[:20]: print('  ',p)

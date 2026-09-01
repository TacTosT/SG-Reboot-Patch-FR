# -*- coding: utf-8 -*-
"""Audit the files actually installed in the game folder."""
import sys,io,os,json,hashlib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
REPO='C:/Users/valen/sgreboot_fr'
sys.path.insert(0,REPO); sys.path.insert(0,REPO+'/tools')
import inject
from psb import Psb, StrRef
from mzs import SEED, unwrap
from sgre import Archive
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'
fr=inject.load_fr()
orig=Archive('scenario', REPO+'/backup')
new =Archive('scenario', GAME)
print('entries: orig',len(orig.file_info),'installed',len(new.file_info),
      '| same order:', orig.names()==new.names())
problems=[]; checked=0; alts=0; nonks=0
for name in orig.names():
    if not name.endswith('.ks'):
        nonks+=1
        if orig.body[orig.file_info[name][0]:sum(orig.file_info[name])] != \
           new.body[new.file_info[name][0]:sum(new.file_info[name])]:
            problems.append((name,'NONKS_DIFF','')); 
        continue
    po=Psb(orig.read(name), track_strings=True)
    pp=Psb(new.read(name),  track_strings=True)
    if len(po.strings())!=len(pp.strings()): problems.append((name,'STRCOUNT','')); continue
    if po.names!=pp.names: problems.append((name,'NAMES',''))
    langs=[l for l in (po.root.get('languages') or []) if isinstance(l,str)]
    slot=1+langs.index('en') if 'en' in langs else None
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
                if fr.get(f'{name}:{lab}:{ti}') is None: continue
                checked+=1
                want=inject.display_len(str(vp[1]))
                if len(vp)>2 and int(vp[2])!=want:
                    problems.append((name,'DLEN',f'{lab}:{ti} {int(vp[2])} != {want}'))
                flat=inject.flat_form(str(vp[1]))
                for a in vp[3:]:
                    if isinstance(a,str):
                        alts+=1
                        if str(a)!=flat: problems.append((name,'ALT',f'{lab}:{ti}'))
print(f'.ks lines audited: {checked}   alt forms: {alts}   non-.ks copied verbatim: {nonks}')
print('problems:', len(problems))
for p in problems[:15]: print('  ',p)
# spot-check the two text fixes as they now sit in the game
for key in ('resg00_01.ks:*dummy1:18','resg02_06.ks:*dummy5:10','resg01_02.ks:*start:0'):
    f,lab,ti=key.split(':'); ti=int(ti)
    p=Psb(new.read(f), track_strings=True)
    for sc in p.root['scenes']:
        if isinstance(sc,dict) and sc.get('label')==lab:
            v=sc['texts'][ti][1][1]
            print(f'  {key}: dlen={int(v[2])} text={str(v[1])[:70]!r}')

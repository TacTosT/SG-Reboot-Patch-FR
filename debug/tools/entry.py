# -*- coding: utf-8 -*-
import json,sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'

def load(root, which):
    idx=unwrap(open(os.path.join(root,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
    p=Psb(idx); fi=p.root['file_info']
    body=open(os.path.join(root,'scenario_body.bin'),'rb').read()
    off,ln=fi[which]
    return Psb(unwrap(body[off:off+ln], SEED+which+'.scn.m'), track_strings=True)

for tag,root in (('ORIG',BACKUP),('PATCHED',GAME)):
    try:
        psb=load(root,'resg01_02.ks')
    except Exception as e:
        print(tag,'FAILED',e); continue
    print('=====',tag,'resg01_02.ks  languages=',psb.root.get('languages'))
    sc=psb.root['scenes'][0]
    print('scene keys:', list(sc.keys()))
    for i in (0,2,11,13):
        e=sc['texts'][i]
        print(f'--- text {i}: len(entry)={len(e)}')
        for j,v in enumerate(e):
            if j==1:
                for k,var in enumerate(v):
                    print(f'    variant[{k}] = {var!r}'[:300])
            else:
                print(f'    entry[{j}] = {v!r}'[:300])

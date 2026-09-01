# -*- coding: utf-8 -*-
import json,sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
def load(n):
    off,ln=fi[n]; return Psb(unwrap(body[off:off+ln], SEED+n+'.scn.m'), track_strings=True)
for n in ('resg01_01.ks','resg01_02.ks'):
    psb=load(n)
    print('==',n,'root keys:',list(psb.root.keys()))
    for k,v in psb.root.items():
        if k!='scenes': print('   ',k,'=',repr(v)[:200])
    for sc in psb.root['scenes']:
        print('   scene label=',sc.get('label'),'firstLine=',sc.get('firstLine'),'lines=',repr(sc.get('lines'))[:120],'spCount=',sc.get('spCount'),'title=',sc.get('title'),'version=',sc.get('version'),'ntexts=',len(sc.get('texts') or []))
        print('   nexts=',repr(sc.get('nexts'))[:400])

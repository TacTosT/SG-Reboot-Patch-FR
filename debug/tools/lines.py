# -*- coding: utf-8 -*-
import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
def load(n):
    off,ln=fi[n]; return Psb(unwrap(body[off:off+ln], SEED+n+'.scn.m'))
n=sys.argv[1]; a=int(sys.argv[2]); b=int(sys.argv[3])
psb=load(n)
L=psb.root['scenes'][0]['lines']
print(n,'lines count',len(L))
for i in range(a,min(b,len(L))):
    print(f'--{i}--', json.dumps(L[i],ensure_ascii=False,default=str)[:600])

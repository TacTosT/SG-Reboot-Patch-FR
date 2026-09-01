# -*- coding: utf-8 -*-
import sys,io,os,re,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
BS=chr(92)
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
samples=[]
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            for vi,v in enumerate(entry[1]):
                if isinstance(v,list) and len(v)>2 and isinstance(v[1],str) and isinstance(v[2],int):
                    samples.append((name,ti,vi,v[1],v[2]))

PCT=re.compile('%[a-zA-Z][^;]*;')
RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]')
ESC=re.compile(re.escape(BS)+'(.)', re.S)

def display_len(t):
    s=PCT.sub('',t)          # %p-1; %p; ... pause codes: not displayed
    s=RUBY.sub('',s)         # [reading] / [reading,N] furigana: not displayed
    s=ESC.sub(lambda m: '' if m.group(1)=='n' else m.group(1), s)   # \n = break, \X = escape
    return len(s)            # <tips,N,label> counts raw, markup included

ok=0; miss=[]
for name,ti,vi,t,dl in samples:
    if display_len(t)==dl: ok+=1
    elif len(miss)<20: miss.append((name,ti,vi,dl,display_len(t),t[:110]))
print(f'{ok}/{len(samples)}  {100*ok/len(samples):.4f}%')
for m in miss: print('  ',m)

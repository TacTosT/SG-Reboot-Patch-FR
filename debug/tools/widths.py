# -*- coding: utf-8 -*-
import sys,io,os,re,json,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
BS=chr(92)
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
PCT=re.compile('%[a-zA-Z][^;]*;'); RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]')
ESC=re.compile(re.escape(BS)+'(.)', re.S)
def dlen(t):
    s=RUBY.sub('',PCT.sub('',t))
    return len(ESC.sub(lambda m:'' if m.group(1)=='n' else m.group(1), s))
def width(v): return 0 if v==0 else (v.bit_length()+7)//8
c=collections.Counter(); over=[]
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    if 'en' not in langs: continue
    slot=1+langs.index('en')
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        lab=scene.get('label') or ''
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            if len(entry[1])<=slot: continue
            v=entry[1][slot]
            if not (isinstance(v,list) and len(v)>2 and isinstance(v[1],str) and isinstance(v[2],int)): continue
            t=fr.get(f'{name}:{lab}:{ti}')
            if t is None: c['no_fr']+=1; continue
            old,new=v[2],dlen(t)
            w=width(old)
            fits = (new==0 and old==0) or (w>0 and new < (1<<(8*w)) and new>0) or (new==old)
            c['total']+=1
            c['same' if new==old else ('fits' if fits else 'NEEDS_WIDER')]+=1
            if not fits and len(over)<12: over.append((name,lab,ti,old,new,w,t[:60]))
print(c)
for o in over: print('  ',o)

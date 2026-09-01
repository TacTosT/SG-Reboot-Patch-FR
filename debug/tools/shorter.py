# -*- coding: utf-8 -*-
"""Where is the French SHORTER than the stale display_len the engine still believes?"""
import sys,io,os,re,json,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from mzs import SEED, unwrap
BS=chr(92)
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'
idx=unwrap(open(os.path.join(GAME,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(GAME,'scenario_body.bin'),'rb').read()
PCT=re.compile('%[a-zA-Z][^;]*;')
RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]')
ESC=re.compile(re.escape(BS)+'(.)', re.S)
def dlen(t):
    s=PCT.sub('',t); s=RUBY.sub('',s)
    return len(ESC.sub(lambda m: '' if m.group(1)=='n' else m.group(1), s))

rows=[]
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    if 'en' not in langs: continue
    slot=1+langs.index('en')
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        lab=scene.get('label')
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            vs=entry[1]
            if len(vs)<=slot: continue
            v=vs[slot]
            if not (isinstance(v,list) and len(v)>2 and isinstance(v[1],str) and isinstance(v[2],int)): continue
            real=dlen(v[1]); stored=v[2]
            rows.append((name,lab,ti,real,stored,v[1]))
tot=len(rows)
short=[r for r in rows if r[3]<r[4]]
long_=[r for r in rows if r[3]>r[4]]
eq=[r for r in rows if r[3]==r[4]]
print(f'lines {tot}: FR shorter than stored {len(short)}  ({100*len(short)/tot:.1f}%) | longer {len(long_)} | equal {len(eq)}')
print('\n-- worst over-reads (stored - real) --')
for r in sorted(short, key=lambda r:r[3]-r[4])[:12]:
    print(f'  {r[0]}:{r[1]}:{r[2]}  real={r[3]} stored={r[4]}  diff={r[4]-r[3]}  {r[5][:70]}')
print('\n-- first files in play order --')
for f in ('resg00_01.ks','resg01_01.ks','resg01_02.ks'):
    sub=[r for r in rows if r[0]==f]
    s=[r for r in sub if r[3]<r[4]]
    print(f'  {f}: {len(s)}/{len(sub)} shorter; max over-read {max([r[4]-r[3] for r in s],default=0)}')
    for r in s[:6]: print(f'      #{r[2]} real={r[3]} stored={r[4]}  {r[5][:60]}')

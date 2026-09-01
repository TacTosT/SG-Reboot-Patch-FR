# -*- coding: utf-8 -*-
"""EN slot: does the injected French carry markup where the original had no alt forms?"""
import sys,io,os,re,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
BS=chr(92)
def arc(root):
    idx=unwrap(open(os.path.join(root,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
    p=Psb(idx)
    return p.root['file_info'], open(os.path.join(root,'scenario_body.bin'),'rb').read()
fi,body=arc('C:/Users/valen/sgreboot_fr/backup')
fiP,bodyP=arc(r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data')
NL=re.compile(re.escape(BS)+'n'); RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]'); PCT=re.compile('%[a-zA-Z][^;]*;')
def markup(t): return bool(NL.search(t) or RUBY.search(t) or PCT.search(t))
c=collections.Counter(); firsts=[]
order=[n for n in fi if n.endswith('.ks')]
for name in order:
    off,ln=fi[name];  po=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    off,ln=fiP[name]; pp=Psb(unwrap(bodyP[off:off+ln], SEED+name+'.scn.m'))
    langs=[l for l in (po.root.get('languages') or []) if isinstance(l,str)]
    if 'en' not in langs: continue
    slot=1+langs.index('en')
    for so,sp in zip(po.root.get('scenes') or [], pp.root.get('scenes') or []):
        if not isinstance(so,dict): continue
        for ti,(eo,ep) in enumerate(zip(so.get('texts') or [], sp.get('texts') or [])):
            if not (isinstance(eo,list) and len(eo)>1 and isinstance(eo[1],list)): continue
            if len(eo[1])<=slot: continue
            vo,vp=eo[1][slot],ep[1][slot]
            if not (isinstance(vo,list) and len(vo)>2 and isinstance(vo[1],str)): continue
            en,fr=vo[1],vp[1]
            nalt=len(vo)-3
            key=(markup(en),markup(fr),nalt)
            c[key]+=1
            if markup(fr) and not markup(en) and nalt==0 and len(firsts)<12:
                firsts.append((name,so.get('label'),ti,en[:55],fr[:70]))
print('(EN has markup, FR has markup, #alt slots) -> count')
for k,v in sorted(c.items()): print('  ',k,v)
print('\nFR gains markup where the EN variant has NO alt slot:')
for f in firsts: print('  ',f)

# -*- coding: utf-8 -*-
"""When do alt forms exist, and what are they?"""
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
NL=re.compile(re.escape(BS)+'n')
RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]')
PCT=re.compile('%[a-zA-Z][^;]*;')
stats=collections.Counter(); ex=collections.defaultdict(list)
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            for vi,v in enumerate(entry[1]):
                if not (isinstance(v,list) and len(v)>2 and isinstance(v[1],str)): continue
                t=v[1]; alts=[a for a in v[3:] if isinstance(a,str)]
                has_nl=bool(NL.search(t)); has_ruby=bool(RUBY.search(t))
                key=(has_nl,has_ruby,len(v)-3,len(alts))
                stats[key]+=1
                if len(ex[key])<2: ex[key].append((name,ti,vi,t[:80],[a[:80] for a in alts]))
for k,c in sorted(stats.items()): print(k,c)
print()
# for those with alts: is alt == text with \n removed and ruby dropped?
ok=collections.Counter(); bad=[]
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            for vi,v in enumerate(entry[1]):
                if not (isinstance(v,list) and len(v)>3): continue
                t=v[1]; alts=[a for a in v[3:] if isinstance(a,str)]
                if not alts: continue
                c1=NL.sub('',t)
                c2=RUBY.sub('',NL.sub('',t))
                c3=RUBY.sub(lambda m:m.group(1),NL.sub('',t))
                for j,a in enumerate(alts):
                    lbl='nl' if a==c1 else ('nl+ruby' if a==c2 else ('nl+reading' if a==c3 else 'OTHER'))
                    ok[(j,lbl)]+=1
                    if lbl=='OTHER' and len(bad)<10: bad.append((name,ti,vi,j,t[:80],a[:80]))
for k,c in sorted(ok.items()): print(k,c)
for b in bad: print('  BAD',b)

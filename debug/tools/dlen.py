# -*- coding: utf-8 -*-
"""Reverse-engineer display_len and the alt-form rule from the ORIGINAL archive."""
import sys,io,os,re,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
idx=unwrap(open(os.path.join(BACKUP,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
p=Psb(idx); fi=p.root['file_info']
body=open(os.path.join(BACKUP,'scenario_body.bin'),'rb').read()

PCT=re.compile(r'%[a-zA-Z][^;]*;')
RUBY=re.compile(r'\[([^\]\[]*?)(?:,(\d+))?\]')
TIPS=re.compile(r'<tips,\s*(\d+)\s*,([^>]*)>')
def strip1(t):   # %p only
    return PCT.sub('',t)
def strip2(t):   # %p + tips->label + ruby bracket removed
    t=PCT.sub('',t); t=TIPS.sub(lambda m:m.group(2),t); t=RUBY.sub('',t); return t

stats=collections.Counter(); bad=[]; altstats=collections.Counter(); altbad=[]
n=0
for name in fi:
    if not name.endswith('.ks'): continue
    off,ln=fi[name]
    psb=Psb(unwrap(body[off:off+ln], SEED+name+'.scn.m'))
    for scene in psb.root.get('scenes') or []:
        if not isinstance(scene,dict): continue
        for ti,entry in enumerate(scene.get('texts') or []):
            if not (isinstance(entry,list) and len(entry)>1 and isinstance(entry[1],list)): continue
            for vi,v in enumerate(entry[1]):
                if not (isinstance(v,list) and len(v)>2 and isinstance(v[1],str) and isinstance(v[2],int)): continue
                t,dl=v[1],v[2]
                n+=1
                cands={'raw':len(t),'nopct':len(strip1(t)),'full':len(strip2(t))}
                ok=[k for k,val in cands.items() if val==dl]
                stats[tuple(sorted(ok))]+=1
                if not ok and len(bad)<15: bad.append((name,ti,vi,dl,cands,t[:110]))
                # alt forms
                if len(v)>3:
                    alts=[a for a in v[3:] if isinstance(a,str)]
                    exp=t.replace('\n','')
                    got=set(alts)
                    altstats[('match' if all(a==exp for a in alts) else 'other', len(alts))]+=1
                    if not all(a==exp for a in alts) and len(altbad)<10:
                        altbad.append((name,ti,vi,t[:80],alts[0][:80]))
                else:
                    altstats[('none',0)]+=1
print('variants examined:',n)
print('\n-- which formula equals display_len --')
for k,v in stats.most_common(): print('  ',k,v)
print('\n-- mismatches --')
for b in bad: print('  ',b)
print('\n-- alt forms --')
for k,v in altstats.most_common(): print('  ',k,v)
for b in altbad: print('  ',b)

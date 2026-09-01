# -*- coding: utf-8 -*-
"""Control: does rewriting a .ks with its OWN strings reproduce it byte-for-byte?"""
import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from psb_write import rebuild_strings
from sgre import Archive
arc=Archive('scenario','C:/Users/valen/sgreboot_fr/backup')
ok=0; bad=[]
for name in arc.names():
    if not name.endswith('.ks'): continue
    raw=arc.read(name)
    out=rebuild_strings(raw, Psb(raw).strings())
    if out==raw: ok+=1
    else:
        d=next((i for i,(a,b) in enumerate(zip(out,raw)) if a!=b), min(len(out),len(raw)))
        bad.append((name, len(raw), len(out), d))
print(f'identity round-trip of rebuild_strings: {ok} byte-identical, {len(bad)} differ')
for b in bad[:10]: print('  ',b)

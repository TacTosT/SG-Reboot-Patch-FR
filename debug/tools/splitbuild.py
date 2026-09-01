# -*- coding: utf-8 -*-
"""Rebuild the archive leaving chosen lines in English. Everything else stays French.

    python bisect.py OUTDIR resg01_02.ks              # whole file English
    python bisect.py OUTDIR resg01_02.ks:0-45         # only those text indices
    python bisect.py OUTDIR resg01_02.ks:%p           # only its %p-carrying lines
    python bisect.py OUTDIR resg01_02.ks:tips         # only its <tips> lines

Shared string slots are dropped along with the line, or the slot would get
French anyway and the test would prove nothing.
"""
import sys, os, re, collections
REPO='C:/Users/valen/sgreboot_fr'
sys.path.insert(0, REPO); sys.path.insert(0, REPO+'/tools')
import inject
from mzs import SEED, wrap, unwrap
from psb import Psb, StrRef
from sgre import Archive

out_dir = sys.argv[1]
specs = sys.argv[2:]
os.makedirs(out_dir, exist_ok=True)
fr = inject.load_fr()
arc = Archive('scenario', REPO+'/backup')

def slots(name):
    psb = Psb(arc.read(name), track_strings=True)
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    slot = 1+langs.index('en')
    out={}
    for sc in psb.root.get('scenes') or []:
        if not isinstance(sc,dict): continue
        lab = sc.get('label') or ''
        for i,e in enumerate(sc.get('texts') or []):
            if not (isinstance(e,list) and len(e)>1 and isinstance(e[1],list)): continue
            if len(e[1])<=slot: continue
            v=e[1][slot]
            if isinstance(v,list) and len(v)>1 and isinstance(v[1],StrRef):
                out[f'{name}:{lab}:{i}'] = (i, v[1].index)
    return out

drop=set()
for spec in specs:
    parts = spec.split(':', 1)
    name = parts[0]
    sel  = parts[1] if len(parts)>1 else None
    ids = slots(name)
    chosen=set()
    for key,(i,ix) in ids.items():
        t = fr.get(key, '')
        if sel is None: ok=True
        elif sel=='%p':  ok = '%p' in t
        elif sel=='tips': ok = '<tips' in t
        elif '-' in sel:
            a,b = sel.split('-'); ok = int(a) <= i <= int(b)
        else: ok = (i == int(sel))
        if ok: chosen.add(key)
    want = {ids[k][1] for k in chosen}
    for key,(i,ix) in ids.items():
        if ix in want: drop.add(key)
print(f'lines left in English: {len(drop)}')
for k in sorted(drop)[:12]: print('   ', k, '|', fr.get(k,'')[:70])
if len(drop)>12: print(f'    ... and {len(drop)-12} more')
for k in drop: fr.pop(k, None)

body = bytearray(); new_info = {}
for name in arc.names():
    off, length = arc.file_info[name]
    packed = arc.body[off:off+length]
    if name.endswith('.ks'):
        out, n, c, dl = inject.patch_one(arc.read(name), name, fr)
        blob = wrap(out, SEED + name + arc.suffix) if (out is not None and n) else packed
    else:
        blob = packed
    new_info[name] = [len(body), len(blob)]
    body += blob
index_name='scenario_info.psb.m'
plain = unwrap(open(os.path.join(REPO,'backup',index_name),'rb').read(), SEED+index_name)
# Poke the numbers in place. Re-encoding the tree ships an index the engine
# silently chokes on - that bug is what this tool spent an evening chasing.
idx = Psb(plain, track_ints=True)
buf = bytearray(plain)
for entry, (off_ref, len_ref) in idx.root['file_info'].items():
    want = new_info[entry]
    assert off_ref.poke(buf, want[0]) and len_ref.poke(buf, want[1]), entry
new_index = bytes(buf)
assert Psb(new_index).root['file_info'] == new_info
assert len(new_index) == len(plain)
open(os.path.join(out_dir,'scenario_body.bin'),'wb').write(bytes(body))
open(os.path.join(out_dir,index_name),'wb').write(wrap(new_index, SEED+index_name))
print('wrote', out_dir)

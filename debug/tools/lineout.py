# -*- coding: utf-8 -*-
"""Rebuild the archive with specific LINE IDs left in English. One variable changed.

    python lineout.py out_dir resg01_01.ks:*start:110 ...
"""
import sys, os
REPO='C:/Users/valen/sgreboot_fr'
sys.path.insert(0, REPO); sys.path.insert(0, REPO+'/tools')
import inject
from mzs import SEED, wrap, unwrap
from psb import Psb, StrRef
from psb_write import rebuild_entries
from sgre import Archive

out_dir = sys.argv[1]
drop = set(sys.argv[2:])
os.makedirs(out_dir, exist_ok=True)
fr = inject.load_fr()
arc = Archive('scenario', REPO+'/backup')

# A line shares its string slot with any line holding the same English. Drop
# those too, or the slot gets French anyway and the test proves nothing.
extra = set()
for key in list(drop):
    name = key.split(':')[0]
    psb = Psb(arc.read(name), track_strings=True)
    langs=[l for l in (psb.root.get('languages') or []) if isinstance(l,str)]
    slot = 1+langs.index('en')
    want = None
    ids = {}
    for sc in psb.root.get('scenes') or []:
        if not isinstance(sc,dict): continue
        lab = sc.get('label') or ''
        for i,e in enumerate(sc.get('texts') or []):
            if not (isinstance(e,list) and len(e)>1 and isinstance(e[1],list)): continue
            if len(e[1])<=slot: continue
            v=e[1][slot]
            if not (isinstance(v,list) and len(v)>1 and isinstance(v[1],StrRef)): continue
            ids[f'{name}:{lab}:{i}'] = v[1].index
    want = ids.get(key)
    if want is None:
        sys.exit('no such line: '+key)
    for k,ix in ids.items():
        if ix == want: extra.add(k)
print('dropping (incl. shared string slots):', sorted(extra))
for k in extra: fr.pop(k, None)

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
index_name = 'scenario_info.psb.m'
plain = unwrap(open(os.path.join(REPO,'backup',index_name),'rb').read(), SEED+index_name)
idx = Psb(plain); root = idx.root
root['file_info'] = {k: new_info[k] for k in root['file_info']}
new_index = rebuild_entries(plain, root, {n:i for i,n in enumerate(idx.names)},
                            {s:i for i,s in enumerate(idx.strings())})
assert Psb(new_index).root['file_info'] == root['file_info']
open(os.path.join(out_dir,'scenario_body.bin'),'wb').write(bytes(body))
open(os.path.join(out_dir,index_name),'wb').write(wrap(new_index, SEED+index_name))
print('wrote', out_dir, len(body), 'bytes')

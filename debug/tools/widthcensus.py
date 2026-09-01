# -*- coding: utf-8 -*-
"""Which PsbArray element widths does the SHIPPED game actually use anywhere?"""
import sys,io,os,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'

cw=collections.Counter(); ew=collections.Counter(); where=collections.defaultdict(list)
def scan_arrays(data, label):
    """Walk a PSB, recording the shape of every array we can reach structurally."""
    p=Psb(data)
    for off,kind in ((p.off_strings,'str_offsets'),(p.off_chunk_offsets,'chunk_offsets'),
                     (p.off_chunk_lengths,'chunk_lengths')):
        n=data[off]-0x0C
        count=int.from_bytes(data[off+1:off+1+n],'little') if n>0 else 0
        cw[n]+=1
        if count:
            m=data[off+1+n]-0x0C
            ew[m]+=1
            if m not in (1,2,4): where[m].append((label,kind,count))

arcs=['scenario','image','motion','config','script','sound','voice','font']
for kind in arcs:
    try: a=Archive(kind, GAME)
    except Exception as e:
        print(kind,'skip',e); continue
    names=a.names()
    done=0
    for nm in names:
        try: d=a.read(nm)
        except Exception: continue
        if d[:4]!=b'PSB\0': continue
        try: scan_arrays(d, f'{kind}/{nm}')
        except Exception: continue
        done+=1
        if done>=400: break
    print(f'{kind:9} scanned {done} PSB entries')
print('\ncount-field widths seen :', dict(sorted(cw.items())))
print('element widths seen     :', dict(sorted(ew.items())))
if where:
    print('\nnon-1/2/4 widths, examples:')
    for m,v in where.items():
        print(f'  width {m}: {len(v)} arrays, e.g. {v[:3]}')
else:
    print('\nno array in the shipped game uses an element width other than 1, 2 or 4.')

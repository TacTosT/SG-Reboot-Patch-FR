# -*- coding: utf-8 -*-
"""Are the embedded resource chunks of every .ks byte-identical after patching?"""
import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
O=Archive('scenario','C:/Users/valen/sgreboot_fr/backup')
P=Archive('scenario', r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data')
tot=0; withchunks=0; bad=[]
for name in O.names():
    if not name.endswith('.ks'): continue
    a=Psb(O.read(name)); b=Psb(P.read(name))
    tot+=1
    if a.chunk_offsets or a.chunk_lengths: withchunks+=1
    if a.chunk_offsets!=b.chunk_offsets or a.chunk_lengths!=b.chunk_lengths:
        bad.append((name,'CHUNK_TABLE',len(a.chunk_offsets),len(b.chunk_offsets))); continue
    for i in range(len(a.chunk_offsets)):
        if a.resource(i)!=b.resource(i):
            bad.append((name,'CHUNK_BYTES',i)); break
    # tail beyond the last chunk
    if a.data[a.off_chunk_data:] != b.data[b.off_chunk_data:]:
        bad.append((name,'TAIL_DIFF',len(a.data)-a.off_chunk_data, len(b.data)-b.off_chunk_data))
print(f'.ks files: {tot}, of which carry chunks: {withchunks}')
print('mismatches:', len(bad))
for x in bad[:15]: print('  ',x)

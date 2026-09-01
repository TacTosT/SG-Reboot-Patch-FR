# -*- coding: utf-8 -*-
"""Any PSB array whose element width changed between original and patched?"""
import sys,io,os,struct,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
import inject

def arr_info(data, off):
    n = data[off] - 0x0C
    count = int.from_bytes(data[off+1:off+1+n], 'little') if n>0 else 0
    if count==0: return (n, 0, 0)
    m = data[off+1+n] - 0x0C
    return (n, count, m)

O=Archive('scenario','C:/Users/valen/sgreboot_fr/backup')
fr=inject.load_fr()
rows=[]
for name in O.names():
    if not name.endswith('.ks'): continue
    raw=O.read(name)
    out,n,c,dl = inject.patch_one(raw, name, fr)
    if out is None or not n: continue
    a=Psb(raw); b=Psb(out)
    ia=arr_info(raw, a.off_strings); ib=arr_info(out, b.off_strings)
    blob_a=a.off_chunk_offsets-a.off_strings_data
    blob_b=b.off_chunk_offsets-b.off_strings_data
    if ia!=ib:
        rows.append((name, ia, ib, blob_a, blob_b))
print('files whose string-offset array changed shape:', len(rows))
print(f'{"file":18} {"orig (cw,count,ew)":22} {"patched":22} {"blob bytes":>12}')
for name,ia,ib,ba,bb in rows:
    flag = '   <-- ELEMENT WIDTH GREW' if ib[2]!=ia[2] else ''
    print(f'{name:18} {str(ia):22} {str(ib):22} {ba:>7,}->{bb:,}{flag}')

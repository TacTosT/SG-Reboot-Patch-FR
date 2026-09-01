# -*- coding: utf-8 -*-
"""Does the rebuilt archive index differ from the original in any parsed value?"""
import sys,io,os,struct
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
name='scenario_info.psb.m'
o=unwrap(open('C:/Users/valen/sgreboot_fr/backup/'+name,'rb').read(), SEED+name)
p=unwrap(open(r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data/'+name,'rb').read(), SEED+name)
po,pp=Psb(o),Psb(p)
print('version',po.version,pp.version,'| names equal:',po.names==pp.names,
      '| strings equal:',po.strings()==pp.strings())
print('root keys orig   :', sorted(po.root))
print('root keys patched:', sorted(pp.root))
for k in sorted(set(po.root)|set(pp.root)):
    a,b=po.root.get(k),pp.root.get(k)
    if k=='file_info':
        print(f'  {k}: {len(a)} vs {len(b)} entries (offsets expected to differ)')
        print(f'      types orig {set(type(x).__name__ for v in a.values() for x in v)}'
              f' / patched {set(type(x).__name__ for v in b.values() for x in v)}')
        continue
    same = (a==b) and (type(a)==type(b))
    print(f'  {k}: {"same" if same else "DIFFERENT"}  orig={repr(a)[:90]}  patched={repr(b)[:90]}')
# type census of every value in the tree
import collections
def census(v,c):
    c[type(v).__name__]+=1
    if isinstance(v,list):
        for x in v: census(x,c)
    elif isinstance(v,dict):
        for x in v.values(): census(x,c)
co,cp=collections.Counter(),collections.Counter()
census(po.root,co); census(pp.root,cp)
print('\nvalue type census  orig:',dict(co))
print('value type census patch:',dict(cp))

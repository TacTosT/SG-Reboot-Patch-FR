# -*- coding: utf-8 -*-
import sys,io,os,json,struct,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from sgre import Archive
arc=Archive('font')
print('font entries:', arc.names())
OUT='fonts'; os.makedirs(OUT,exist_ok=True)
for n in arc.names():
    d=arc.read(n)
    open(os.path.join(OUT,n),'wb').write(d)
    print(' ',n,len(d),d[:8])

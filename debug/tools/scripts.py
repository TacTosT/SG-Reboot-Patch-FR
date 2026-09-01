# -*- coding: utf-8 -*-
import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from sgre import Archive
arc=Archive('script')
ns=arc.names()
print(len(ns),'entries in script archive')
for n in ns: print('  ',n)

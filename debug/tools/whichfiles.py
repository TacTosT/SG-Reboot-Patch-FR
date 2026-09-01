# -*- coding: utf-8 -*-
"""Which archive entries does the patch actually modify?"""
import json,sys,io,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from sgre import Archive
fr={json.loads(l)['id'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
byfile=collections.Counter(i.split(':')[0] for i in fr)
arc=Archive('scenario','C:/Users/valen/sgreboot_fr/backup')
names=arc.names()
print(f'{len(names)} entries in the archive\n')
print('entries with NO French (left untouched by the patch):')
for n in names:
    if n not in byfile: print(f'   {n}')
print('\nnon-scenario-looking entries that DO get French:')
for n in names:
    if n in byfile and not n.startswith('resg'):
        print(f'   {n}: {byfile[n]} lines')

# -*- coding: utf-8 -*-
"""Characters the French uses that the shipped English never uses anywhere."""
import json,sys,io,re,collections,unicodedata
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
src={}
for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8'):
    r=json.loads(l); src[r['id']]=r
en_all=set()
for r in src.values(): en_all |= set(r['texts'].get('en',''))
print('distinct chars in ALL shipped English:', len(en_all))

# invisible / control characters anywhere in the French
weird=collections.defaultdict(list)
for i,t in fr.items():
    for c in set(t):
        cat=unicodedata.category(c)
        if cat in ('Cc','Cf','Co','Cs','Zl','Zp') or c in ('\u00a0','\u200b','\u200e','\u200f','\ufeff','\u2028','\u2029'):
            weird[c].append(i)
print('\ninvisible/control chars in the French:', len(weird))
for c,ids in weird.items():
    print(f'  U+{ord(c):04X} {unicodedata.category(c)} in {len(ids)} lines, e.g. {ids[:3]}')

print('\n-- per file: chars used in FR but never in ANY shipped English --')
per=collections.defaultdict(set)
for i,t in fr.items(): per[i.split(':')[0]] |= set(t)
for f in ('resg00_01.ks','resg01_01.ks','resg01_02.ks','resg01_03.ks'):
    novel=sorted(per[f]-en_all)
    print(f'  {f:16} {len(novel):3}  ' + ' '.join(f'U+{ord(c):04X}({c})' for c in novel))

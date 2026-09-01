# -*- coding: utf-8 -*-
import json,sys,io,re,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
src=[json.loads(l) for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8')]
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
TAG=re.compile(r'%p-?\d*;|<tips,\s*\d+\s*,([^>]*)>|\[[^\]]*\]')
def strip(t):
    t=re.sub(r'%p-?\d*;','',t)
    t=re.sub(r'<tips,\s*\d+\s*,([^>]*)>',r'\1',t)
    t=re.sub(r'\[[^\]\[]*?,\d+\]','',t)
    t=re.sub(r'\[[^\]\[]*?\]','',t)
    return t
per=collections.defaultdict(list)
for r in src:
    t=fr.get(r['id'],'')
    per[r['file']].append((len(strip(t)), r['text_index'], t))
order=sorted(per)
print('file        n   maxFRstripped  (top line)')
for f in order[:20]:
    rows=sorted(per[f],reverse=True)
    print(f'{f:16} {len(per[f]):4}  max={rows[0][0]:4} at #{rows[0][1]}  {rows[0][2][:70]}')
# global outliers
allrows=[(l,f,i,t) for f,v in per.items() for l,i,t in v]
allrows.sort(reverse=True)
print('\n== 25 longest FR lines in the whole game (tags stripped) ==')
for l,f,i,t in allrows[:25]:
    print(f'  {l:4} {f}:{i}  {t[:110]}')
# per-segment max for lines the player reaches first
print('\n== max per line-count of \n segments ==')
seg=[]
for r in src:
    t=fr.get(r['id'],'')
    for part in strip(t).split('\n'):
        seg.append((len(part), r['id'], part))
seg.sort(reverse=True)
for l,i,p in seg[:15]: print(f'  {l:4} {i}  {p[:110]}')

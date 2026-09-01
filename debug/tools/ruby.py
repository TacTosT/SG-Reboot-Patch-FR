# -*- coding: utf-8 -*-
"""Every furigana tag in the French: does its span index stay inside the line?"""
import json,sys,io,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
src={}
for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8'):
    r=json.loads(l); src[r['id']]=r['texts'].get('ja','')
RUBY=re.compile(r'\[([^\]\[]*?),(\d+)\]')
PLAIN=re.compile(r'\[([^\]\[,]*)\]')
bad=[]; rows=[]
for i,t in fr.items():
    for m in RUBY.finditer(t):
        n=int(m.group(2)); rest=t[m.end():]
        covered=rest[:n+1]
        rows.append((i,m.group(1),n,covered,len(rest)))
        if n+1>len(rest): bad.append((i,'OVERRUN',m.group(0),n,len(rest),t))
        elif n>60: bad.append((i,'HUGE_N',m.group(0),n,len(rest),t))
    for m in PLAIN.finditer(t):
        rest=t[m.end():]
        if not rest: bad.append((i,'PLAIN_AT_END',m.group(0),0,0,t))
print('semantic ruby tags in FR:',len(rows))
print('problems:',len(bad))
for b in bad[:20]: print('  ',b[0],b[1],b[2],'N=',b[3],'rest=',b[4],'|',b[5][:90])
print('\n-- all semantic ruby tags, covered span --')
for i,read,n,cov,rl in rows:
    flag='' if cov.strip() and not cov.startswith(' ') else '   <-- span starts/ends oddly'
    print(f'  {i:38} [{read},{n}] covers {cov!r}{flag}')

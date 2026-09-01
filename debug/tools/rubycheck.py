# -*- coding: utf-8 -*-
"""Ruby spans that cross markup or stop mid-word."""
import json,sys,io,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
RUBY=re.compile(r'\[([^\]\[]*?),(\d+)\]')
bad=[]
for i,t in fr.items():
    for m in RUBY.finditer(t):
        n=int(m.group(2)); rest=t[m.end():]; cov=rest[:n+1]; after=rest[n+1:]
        why=[]
        if re.search(r'[<>%\\[\]]', cov): why.append('span crosses markup')
        if after and after[0].isalpha() and cov and cov[-1].isalpha(): why.append('span ends mid-word')
        if cov != cov.strip(): why.append('span has edge whitespace')
        if why: bad.append((i, m.group(0), cov, after[:20], '; '.join(why), t))
print('suspect ruby spans:', len(bad))
for b in bad:
    print(f'\n  {b[0]}\n    tag {b[1]}  covers {b[2]!r}  then {b[3]!r}\n    -> {b[4]}\n    {b[5][:120]}')

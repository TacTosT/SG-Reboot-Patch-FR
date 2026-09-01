# -*- coding: utf-8 -*-
import sys,io,os,json,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from sgre import Archive
arc=Archive('font')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
used=collections.Counter()
for t in fr.values(): used.update(t)
for n in ('textfont24','textfont12'):
    p=Psb(arc.read(n))
    code=p.root['code']
    print(f'== {n}: {len(code)} glyphs, label={p.root.get("label")!r} spec={p.root.get("spec")!r} source={str(p.root.get("source"))[:60]}')
    miss={c:k for c,k in used.items() if c not in code}
    print('   FR chars missing:',len(miss))
    for c,k in sorted(miss.items(), key=lambda x:-x[1])[:25]:
        print(f'     U+{ord(c):04X} {c!r} x{k}')

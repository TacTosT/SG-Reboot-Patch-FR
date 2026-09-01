# -*- coding: utf-8 -*-
import json, re, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC='C:/Users/valen/sgreboot_fr/extracted/all.jsonl'
FR ='C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl'

src={}
for l in open(SRC,encoding='utf-8'):
    r=json.loads(l); src[r['id']]=r
fr={}
for l in open(FR,encoding='utf-8'):
    r=json.loads(l); fr[r['id']]=r['fr']

print("src lines", len(src), "fr lines", len(fr))
print("missing in fr:", len(set(src)-set(fr)))
print("extra in fr  :", len(set(fr)-set(src)))

# inventory of every %-code and bracket construct across the whole JA corpus
pct=collections.Counter(); brk=collections.Counter(); ang=collections.Counter()
for r in src.values():
    for code,t in r['texts'].items():
        if not isinstance(t,str): continue
        for m in re.finditer(r'%[^;]{0,20};?', t): pct[(code,m.group(0)[:6])]+=0
for r in src.values():
    t=r['texts'].get('ja','')
    for m in re.finditer(r'%.', t): pct[m.group(0)]+=1
    for m in re.finditer(r'\[[^\]\[]*\]', t): brk[re.sub(r'[^,\d\]\[]','X',m.group(0))]+=1
    for m in re.finditer(r'<[^>]*>', t): ang[m.group(0).split(',')[0]+'>']+=1
print("\n-- %% codes in JA --"); [print(' ',k,v) for k,v in pct.most_common(30)]
print("\n-- bracket shapes in JA --"); [print(' ',k,v) for k,v in brk.most_common(15)]
print("\n-- angle tags in JA --"); [print(' ',k,v) for k,v in ang.most_common(15)]

# same for EN (the slot we overwrite) and FR
for label,getter in (("EN", lambda r: r['texts'].get('en','')), ):
    p=collections.Counter(); b=collections.Counter(); a=collections.Counter()
    for r in src.values():
        t=getter(r)
        for m in re.finditer(r'%.', t): p[m.group(0)]+=1
        for m in re.finditer(r'\[[^\]\[]*\]', t): b[re.sub(r'[^,\d\]\[]','X',m.group(0))]+=1
        for m in re.finditer(r'<[^>]*>', t): a[m.group(0).split(',')[0]+'>']+=1
    print(f"\n-- %% codes in {label} --"); [print(' ',k,v) for k,v in p.most_common(20)]
    print(f"-- bracket shapes in {label} --"); [print(' ',k,v) for k,v in b.most_common(10)]
    print(f"-- angle tags in {label} --"); [print(' ',k,v) for k,v in a.most_common(10)]

p=collections.Counter(); b=collections.Counter(); a=collections.Counter()
for t in fr.values():
    for m in re.finditer(r'%.', t): p[m.group(0)]+=1
    for m in re.finditer(r'\[[^\]\[]*\]', t): b[re.sub(r'[^,\d\]\[]','X',m.group(0))]+=1
    for m in re.finditer(r'<[^>]*>', t): a[m.group(0).split(',')[0]+'>']+=1
print("\n-- %% codes in FR --"); [print(' ',k,v) for k,v in p.most_common(20)]
print("-- bracket shapes in FR --"); [print(' ',k,v) for k,v in b.most_common(10)]
print("-- angle tags in FR --"); [print(' ',k,v) for k,v in a.most_common(10)]

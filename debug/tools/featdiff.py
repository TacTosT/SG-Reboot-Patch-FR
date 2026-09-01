# -*- coding: utf-8 -*-
"""What does the French in resg01_02 have that the two files that DO work don't?"""
import json,sys,io,re,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
def feats(t):
    f=set()
    if t.startswith('%p'): f.add('starts with %p')
    if re.search(r'%p-?\d*;$', t): f.add('ends with a pause code')
    if t.endswith('─'): f.add('ends with a dash U+2500')
    if '\n' in t: f.add('has \n')
    if '<tips' in t: f.add('has <tips>')
    if re.search(r'\[[^\]]*,\d+\]', t): f.add('has semantic ruby')
    if re.search(r'\[[^\],]*\]', t): f.add('has plain ruby')
    if not t.strip(): f.add('EMPTY')
    if re.match(r'^[\W_]+$', t): f.add('punctuation only')
    if '%p' in t and '\n' in t: f.add('%p AND \n together')
    if t.count('%p')>4: f.add('more than 4 %p')
    if re.search(r'%p-?\d*;\s*$', t) and len(t)<20: f.add('short line ending in pause')
    return f
per={}
for i,t in fr.items():
    f=i.split(':')[0]
    per.setdefault(f,collections.Counter()).update(feats(t))
    per[f]['chars']=0
work=set()
for f in ('resg00_01.ks','resg01_01.ks'):
    work |= set(per[f])
tgt=set(per['resg01_02.ks'])
print('features in resg01_02 that resg00_01/resg01_01 do NOT have:')
for k in sorted(tgt-work): print('  ',k, per['resg01_02.ks'][k])
print('\nfeature counts side by side:')
keys=sorted(work|tgt)
print(f"  {'feature':32} {'00_01':>7} {'01_01':>7} {'01_02':>7}")
for k in keys:
    if k=='chars': continue
    print(f"  {k:32} {per['resg00_01.ks'][k]:>7} {per['resg01_01.ks'][k]:>7} {per['resg01_02.ks'][k]:>7}")
# character sets
cs={f:set(''.join(t for i,t in fr.items() if i.startswith(f))) for f in ('resg00_01.ks','resg01_01.ks','resg01_02.ks')}
new=cs['resg01_02.ks']-cs['resg00_01.ks']-cs['resg01_01.ks']
print('\ncharacters unique to resg01_02:', sorted(new), [f'U+{ord(c):04X}' for c in sorted(new)])

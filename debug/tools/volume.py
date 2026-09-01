# -*- coding: utf-8 -*-
"""Text volume per scene, English as shipped vs French, in play order."""
import json,sys,io,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
src=[json.loads(l) for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8')]
sc=collections.OrderedDict()
for r in src:
    key=(r['file'], r['scene'])
    d=sc.setdefault(key, {'n':0,'en':0,'fr':0,'ja':0})
    d['n']+=1
    d['en']+=len(r['texts'].get('en',''))
    d['ja']+=len(r['texts'].get('ja',''))
    d['fr']+=len(fr.get(r['id'],''))
rows=[(k,v) for k,v in sc.items() if k[0].startswith(('resg00','resg01','resg02'))]
print(f'{"file":15} {"scene":18} {"lines":>5} {"EN chars":>9} {"FR chars":>9} {"FR/EN":>6}')
for (f,s),v in rows[:30]:
    ratio=v['fr']/v['en'] if v['en'] else 0
    print(f'{f:15} {s:18} {v["n"]:>5} {v["en"]:>9,} {v["fr"]:>9,} {ratio:>6.2f}')
print('\n-- the 12 biggest scenes in the whole game, by French volume --')
allr=sorted(sc.items(), key=lambda kv:-kv[1]['fr'])
for (f,s),v in allr[:12]:
    print(f'  {f:15} {s:18} {v["n"]:>5} lines  EN {v["en"]:>7,}  FR {v["fr"]:>7,}')
print('\n-- biggest by LINE COUNT in a single scene --')
allc=sorted(sc.items(), key=lambda kv:-kv[1]['n'])
for (f,s),v in allc[:12]:
    print(f'  {f:15} {s:18} {v["n"]:>5} lines  EN {v["en"]:>7,}  FR {v["fr"]:>7,}')

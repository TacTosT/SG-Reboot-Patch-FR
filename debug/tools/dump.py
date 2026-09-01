# -*- coding: utf-8 -*-
import json,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
src=[json.loads(l) for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8')]
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
f=sys.argv[1]; a=int(sys.argv[2]); b=int(sys.argv[3])
for r in src:
    if r['file']==f and a<=r['text_index']<=b:
        print(f"#{r['text_index']:3} [{r['scene']}] {r['speaker'] or '(narr)'}")
        print("  JA:",r['texts'].get('ja',''))
        print("  EN:",r['texts'].get('en',''))
        print("  FR:",fr.get(r['id'],''))

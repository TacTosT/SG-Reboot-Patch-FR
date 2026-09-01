# -*- coding: utf-8 -*-
import json,sys,io,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
src=[json.loads(l) for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8')]
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
pat=re.compile(r'一時間前|１時間前|時間前')
for r in src:
    if r['file'].startswith(('resg01_01','resg01_02','resg00_01')) and pat.search(r['texts'].get('ja','')):
        print(r['id'], '|', r['texts']['ja'])
        print('   EN:', r['texts'].get('en',''))
        print('   FR:', fr.get(r['id'],''))
print('---- first 25 lines of resg01_01 ----')
n=0
for r in src:
    if r['file']=='resg01_01.ks':
        print(r['id'],'|',r['speaker'],'|',r['texts']['ja'][:60])
        n+=1
        if n>25: break

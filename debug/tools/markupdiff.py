# -*- coding: utf-8 -*-
"""Markup tokens: Japanese source vs injected French, line by line."""
import json,sys,io,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
BS=chr(92)
fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
src={}
for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8'):
    r=json.loads(l); src[r['id']]=r
TOK=re.compile('|'.join([
    r'<[^>]*>',                      # tips
    r'%[^;]{0,12};',                 # pause codes
    r'%',                            # bare percent
    re.escape(BS)+r'.',              # escapes
    r'\[[^\]\[]*\]',                 # ruby
    r'[<>]',                         # stray angle
]))
target=sys.argv[1] if len(sys.argv)>1 else 'resg01_02.ks'
rows=[(i,r) for i,r in src.items() if r['file']==target]
rows.sort(key=lambda x:x[1]['text_index'])
print(f'{"#":>4}  {"JA tokens":<38} {"EN tokens":<26} FR tokens')
diffs=[]
for i,r in rows:
    ja=TOK.findall(r['texts'].get('ja','')); en=TOK.findall(r['texts'].get('en',''))
    f =TOK.findall(fr.get(i,''))
    if ja!=f or en!=f:
        mark='  <<<' if ja!=f else ''
        print(f'{r["text_index"]:>4}  {str(ja):<38} {str(en):<26} {str(f)}{mark}')
        if ja!=f: diffs.append((i,ja,en,f,fr.get(i,'')))
print(f'\nlines whose FR markup differs from the JA source: {len(diffs)}')
for i,ja,en,f,t in diffs:
    print(f'\n  {i}\n    JA {ja}\n    FR {f}\n    {t[:150]}')

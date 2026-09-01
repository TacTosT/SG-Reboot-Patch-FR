# -*- coding: utf-8 -*-
"""Compare engine-parsed markup between the JA source and the FR translation."""
import json,re,sys,io,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
src={}
for l in open('C:/Users/valen/sgreboot_fr/extracted/all.jsonl',encoding='utf-8'):
    r=json.loads(l); src[r['id']]=r
fr={}
for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8'):
    r=json.loads(l); fr[r['id']]=r['fr']

RUBY = re.compile(r'\[([^\]\[]*?),(\d+)\]')     # semantic furigana with span index
RUBY0= re.compile(r'\[([^\]\[,]*)\]')           # plain furigana
TIPS = re.compile(r'<tips,\s*(\d+)\s*,([^>]*)>')
PCT  = re.compile(r'%[a-zA-Z]-?\d*;?')
UNCLOSED_BRK = re.compile(r'\[[^\]]*$|^[^\[]*\]')

probs=collections.defaultdict(list)
for i,t in fr.items():
    ja=src[i]['texts'].get('ja','')
    # 1. unbalanced brackets / angle brackets
    if t.count('[')!=t.count(']'): probs['BRACKET_UNBALANCED'].append((i,t))
    if t.count('<')!=t.count('>'): probs['ANGLE_UNBALANCED'].append((i,t))
    # 2. tips tag well-formedness
    if t.count('<tips')!=len(TIPS.findall(t)): probs['TIPS_MALFORMED'].append((i,t))
    if len(TIPS.findall(t))!=len(TIPS.findall(ja)): probs['TIPS_COUNT'].append((i,ja,t))
    # 3. %-code parity and shape
    if len(PCT.findall(t))!=len(PCT.findall(ja)): probs['PCT_COUNT'].append((i,ja,t))
    for m in re.finditer(r'%[a-zA-Z][^;]{0,10}', t):
        if not m.group(0).startswith('%p'): probs['PCT_UNKNOWN'].append((i,m.group(0),t))
    for m in re.finditer(r'%p[^;]*', t):
        if not re.fullmatch(r'%p(-?\d+)?', m.group(0)): probs['PCT_SHAPE'].append((i,m.group(0),t))
    if re.search(r'%p[^;]*(?!;)$', t) and not t.endswith(';') and '%p' in t:
        pass
    for m in re.finditer(r'%p[-\d]*(?![;\d])', t):
        probs['PCT_NOSEMI'].append((i,m.group(0),t))
    # 4. ruby span index vs following text length
    for m in RUBY.finditer(t):
        n=int(m.group(2)); rest=t[m.end():]
        if n+1>len(rest): probs['RUBY_OVERRUN'].append((i,m.group(0),n,len(rest),t))
    # 5. newline parity
    if ja.count('\n')!=t.count('\n'): probs['NEWLINE'].append((i,ja,t))
    # 6. characters outside what a Latin font plausibly has
    bad=set(re.findall(r'[^\x09\x0a\x20-\x7e\u00a0-\u024f\u2010-\u203a\u2500\u20ac…«»–—’‘“”€]',t))
    if bad: probs['ODD_CHARS'].append((i,''.join(sorted(bad)),t))

for k in sorted(probs):
    v=probs[k]
    print(f"\n=== {k}: {len(v)} ===")
    for row in v[:12]:
        print('  ', row[0])
        for x in row[1:]: print('      ', repr(x)[:180])

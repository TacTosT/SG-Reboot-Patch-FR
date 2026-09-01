# -*- coding: utf-8 -*-
"""Which characters used by the French translation are missing from each shipped font?"""
import sys,io,os,json,struct,collections,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')

def cmap_chars(path):
    d=open(path,'rb').read()
    n=struct.unpack_from('>H',d,4)[0]
    tabs={}
    for i in range(n):
        tag,chk,off,ln=struct.unpack_from('>4sIII',d,12+16*i)
        tabs[tag]=(off,ln)
    if b'cmap' not in tabs: return None
    co=tabs[b'cmap'][0]
    nt=struct.unpack_from('>H',d,co+2)[0]
    chars=set()
    for i in range(nt):
        pid,eid,so=struct.unpack_from('>HHI',d,co+4+8*i)
        so+=co
        fmt=struct.unpack_from('>H',d,so)[0]
        if fmt==4:
            segx2=struct.unpack_from('>H',d,so+6)[0]; seg=segx2//2
            ends=[struct.unpack_from('>H',d,so+14+2*j)[0] for j in range(seg)]
            starts=[struct.unpack_from('>H',d,so+16+segx2+2*j)[0] for j in range(seg)]
            for s,e in zip(starts,ends):
                if e==0xFFFF and s==0xFFFF: continue
                if e-s>0x20000: continue
                chars.update(range(s,e+1))
        elif fmt==12:
            ng=struct.unpack_from('>I',d,so+12)[0]
            for j in range(ng):
                s,e,g=struct.unpack_from('>III',d,so+16+12*j)
                if e-s>0x20000: continue
                chars.update(range(s,e+1))
    return chars

fr={json.loads(l)['id']:json.loads(l)['fr'] for l in open('C:/Users/valen/sgreboot_fr/extracted/all_fr.jsonl',encoding='utf-8')}
used=collections.Counter()
for t in fr.values(): used.update(t)
print('distinct chars in the FR translation:', len(used))

for f in sorted(os.listdir('fonts')):
    if not f.endswith(('.otf.m','.ttf.m')): continue
    try: cs=cmap_chars(os.path.join('fonts',f))
    except Exception as e: print(f,'ERR',e); continue
    missing={c:n for c,n in used.items() if ord(c) not in cs}
    print(f'\n{f:34} glyphs={len(cs):6}  missing FR chars: {len(missing)}')
    for c,n in sorted(missing.items(), key=lambda x:-x[1])[:20]:
        ids=[i for i,t in fr.items() if c in t][:2]
        print(f'    U+{ord(c):04X} {c!r} x{n}   e.g. {ids}')

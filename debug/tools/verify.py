# -*- coding: utf-8 -*-
"""Deep-compare the patched archive against the original: structure must be identical."""
import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb, StrRef
from mzs import SEED, unwrap
BACKUP='C:/Users/valen/sgreboot_fr/backup'
GAME=r'C:/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data'

def openarc(root):
    idx=unwrap(open(os.path.join(root,'scenario_info.psb.m'),'rb').read(), SEED+'scenario_info.psb.m')
    p=Psb(idx)
    body=open(os.path.join(root,'scenario_body.bin'),'rb').read()
    return p.root['file_info'], body

fi_o,body_o=openarc(BACKUP)
fi_p,body_p=openarc(GAME)
print('entries orig',len(fi_o),'patched',len(fi_p))
print('same key set:', set(fi_o)==set(fi_p))
print('same order  :', list(fi_o)==list(fi_p))

def skeleton(v):
    """structure with strings replaced by a placeholder"""
    if isinstance(v,str): return '\x00S'
    if isinstance(v,list): return [skeleton(x) for x in v]
    if isinstance(v,dict): return {k:skeleton(x) for k,x in v.items()}
    return v

bad=[]
for name in fi_o:
    off,ln=fi_o[name]
    try: raw_o=unwrap(body_o[off:off+ln], SEED+name+'.scn.m')
    except Exception as e: raw_o=None
    off,ln=fi_p[name]
    try: raw_p=unwrap(body_p[off:off+ln], SEED+name+'.scn.m')
    except Exception as e:
        bad.append((name,'DECRYPT_FAIL',str(e))); continue
    if raw_o is None: continue
    if not name.endswith('.ks'):
        if raw_o!=raw_p: bad.append((name,'NONKS_DIFF',''))
        continue
    try:
        po=Psb(raw_o,track_strings=True); pp=Psb(raw_p,track_strings=True)
    except Exception as e:
        bad.append((name,'PARSE_FAIL',str(e))); continue
    so,sp=po.strings(),pp.strings()
    if len(so)!=len(sp): bad.append((name,'STRCOUNT',f'{len(so)} -> {len(sp)}')); continue
    if po.names!=pp.names: bad.append((name,'NAMES',''))
    if skeleton(po.root)!=skeleton(pp.root): bad.append((name,'TREE',''))
    # any string that lost content / became empty
    for i,(a,b) in enumerate(zip(so,sp)):
        if a and not b: bad.append((name,'STR_EMPTIED',f'idx {i}: {a!r}'))
print('\nproblems:',len(bad))
for b in bad[:40]: print('  ',b)

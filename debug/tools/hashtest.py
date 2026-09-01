# -*- coding: utf-8 -*-
"""Can the stored `hash` be reproduced from the file content?"""
import sys,io,os,hashlib,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
from mzs import SEED, unwrap
from sgre import Archive
arc=Archive('scenario','C:/Users/valen/sgreboot_fr/backup')
for name in ('resg01_01.ks','resg01_02.ks','resg00_01.ks'):
    plain=arc.read(name)
    off,ln=arc.file_info[name]; packed=arc.body[off:off+ln]
    psb=Psb(plain)
    want=psb.root.get('hash')
    cands={
      'md5(plain)':hashlib.md5(plain).hexdigest(),
      'md5(packed)':hashlib.md5(packed).hexdigest(),
      'md5(name)':hashlib.md5(name.encode()).hexdigest(),
      'md5(name.utf16)':hashlib.md5(name.encode('utf-16-le')).hexdigest(),
      'md5(stem)':hashlib.md5(name[:-3].encode()).hexdigest(),
      'sha1(plain)[:32]':hashlib.sha1(plain).hexdigest()[:32],
      'md5(entries..end)':hashlib.md5(plain[psb.off_entries:]).hexdigest(),
      'md5(strings blob)':hashlib.md5(plain[psb.off_strings_data:psb.off_chunk_offsets]).hexdigest(),
    }
    print(f'== {name}  stored hash = {want}')
    hit=[k for k,v in cands.items() if v==want]
    for k,v in cands.items(): print(f'   {k:22} {v}{"   <== MATCH" if v==want else ""}')
    print('   match:', hit or 'none')

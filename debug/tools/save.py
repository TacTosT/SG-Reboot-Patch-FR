# -*- coding: utf-8 -*-
import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from psb import Psb
SD='C:/Users/valen/Documents/My Games/mages_steam/STEINS;GATE REBOOT/<steamid>'
for f in ('meta_001_0000.bin','meta_001_0006.bin','meta_000_0000.bin'):
    d=open(os.path.join(SD,f),'rb').read()
    p=Psb(d)
    print('===',f)
    print(json.dumps(p.root, ensure_ascii=False, indent=1, default=str)[:2000])

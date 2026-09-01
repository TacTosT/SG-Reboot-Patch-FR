# -*- coding: utf-8 -*-
import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
sys.path.insert(0,'C:/Users/valen/sgreboot_fr/tools')
from sgre import Archive
arc=Archive('script')
OUT='C:/Users/valen/AppData/Local/Temp/claude/C--WINDOWS-system32/7a4f67bb-bb87-45e7-a59a-22268aba162c/scratchpad/nut'
os.makedirs(OUT,exist_ok=True)
for n in arc.names():
    d=arc.read(n)
    open(os.path.join(OUT,n+'.bin'),'wb').write(d)
print('dumped. sample header of message:', open(os.path.join(OUT,'message.bin'),'rb').read(16))

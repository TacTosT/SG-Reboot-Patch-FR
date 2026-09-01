# -*- coding: utf-8 -*-
import sys,io,os,re,struct,glob
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
D='C:/Users/valen/AppData/Local/Temp/claude/C--WINDOWS-system32/7a4f67bb-bb87-45e7-a59a-22268aba162c/scratchpad/nut'
PAT=re.compile(rb'\x10\x00\x00\x08')
def strs(path):
    d=open(path,'rb').read(); out=[]
    for m in PAT.finditer(d):
        p=m.end()
        if p+4>len(d): continue
        n=struct.unpack_from('<I',d,p)[0]
        if 0<n<4096 and p+4+n<=len(d):
            s=d[p+4:p+4+n]
            try: out.append(s.decode('utf-8'))
            except: pass
    return out
if len(sys.argv)>1 and sys.argv[1]=='--grep':
    pat=re.compile(sys.argv[2], re.I)
    for f in sorted(glob.glob(D+'/*.bin')):
        hits=[s for s in strs(f) if pat.search(s)]
        if hits:
            print('==',os.path.basename(f))
            for h in dict.fromkeys(hits): print('   ',repr(h)[:200])
else:
    f=os.path.join(D, sys.argv[1]+'.bin')
    for s in dict.fromkeys(strs(f)): print(repr(s)[:200])

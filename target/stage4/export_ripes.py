#!/usr/bin/env python3
"""Export the handwritten source plus literal read-only bytes for Ripes editor."""
from pathlib import Path
import argparse,re,subprocess
R=Path(__file__).resolve().parents[2];D=R/'target/stage4'
p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--delay',type=int,default=1000000);p.add_argument('--output');p.add_argument('--vector',default='21345671111111');p.add_argument('--expect',type=int,default=-1);a=p.parse_args()
if a.delay < 0 or a.delay > 2147483647:raise SystemExit('Delay must be a nonnegative signed 32-bit integer')
if len(a.vector)!=14 or not a.vector.isascii() or not a.vector.isdigit():raise SystemExit('Expected 14 ASCII digits')
parts=[]
for name in ['frontend.S','search.S']+(['renderer.S'] if a.render else []):
    text=subprocess.check_output(['/usr/bin/riscv64-unknown-elf-gcc','-E','-P','-x','assembler-with-cpp','-DREVISION=2','-DRENDER='+str(int(a.render)),*(['-DRENDER_DELAY='+str(a.delay)] if a.render else []),str(D/name)],text=True)
    text=re.sub(r'^\.section \.text(?:\.start)?$', '.text',text,flags=re.M)
    text=re.sub(r'^\.section \.(?:rodata|bss|data)$','.data',text,flags=re.M)
    text=re.sub(r'^\.balign 2$','.align 1',text,flags=re.M)
    text=re.sub(r'^\.balign 4$','.align 2',text,flags=re.M)
    text=text.replace('.space ','.zero ')
    def half(m):
        values=[int(x.strip()) for x in m.group(1).split(',')]
        return '.byte '+','.join(str(v) for x in values for v in [x&255,x>>8])
    text=re.sub(r'\.half ([0-9,]+)',half,text)
    pointers=re.search(r'^move_names: .word .*$',text,re.M)
    if pointers:
        line=pointers.group(0)
        text=text.replace(line+'\n','')
        text=re.sub(r'(newline: .asciz .*\n)',lambda m:m.group(0)+'.align 2\n'+line+'\n',text)
    parts.append(text)
data=(R/'target/stage2/tables.bin').read_bytes()
parts.append('.data\n.align 2\nsearch_tables:\n'+'\n'.join('.byte '+','.join(map(str,data[i:i+32])) for i in range(0,len(data),32)))
parts.append('\ninput_vector: .asciz "'+a.vector+'"\n.align 2\nexpected_length: .word '+str(a.expect)+'\n')
out=D/'ripes';out.mkdir(exist_ok=True);path=out/(a.output or a.vector+'.s');path.write_text('\n'.join(parts));print(path)







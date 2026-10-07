#!/usr/bin/env python3
"""Build handwritten RV32I from an arbitrary inlined vector; audit linked bytes."""
from pathlib import Path
import argparse,json,re,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2];DIR=ROOT/'target/stage4'
p=argparse.ArgumentParser();p.add_argument('--vector',default='21345671111111');p.add_argument('--expect',type=int,default=-1);p.add_argument('--revision',type=int,choices=[0,1,2],default=2);p.add_argument('--render',action='store_true');p.add_argument('--render-test',action='store_true');p.add_argument('--renderer-model',action='store_true');a=p.parse_args()
if len(a.vector)!=14 or not a.vector.isascii() or not a.vector.isdigit():raise SystemExit('Expected 14 ASCII digits')
b=DIR/'build'/(f'asm-r{a.revision}'+('-render-test' if a.render_test else '-renderer-model' if a.renderer_model else ''))/a.vector;b.mkdir(parents=True,exist_ok=True)
(b/'data.s').write_text('.section .rodata\n.balign 4\n.globl search_tables\nsearch_tables:\n.incbin "target/stage2/tables.bin"\n.globl input_vector\ninput_vector:\n.asciz "'+a.vector+'"\n.balign 4\n.globl expected_length\nexpected_length:\n.word '+str(a.expect)+'\n')
if a.render_test:
    with (b/'data.s').open('a') as fixture:
        fixture.write('.globl expected_frames\nexpected_frames:\n.incbin '+chr(34)+'target/stage4/fixtures/'+a.vector+'.bin'+chr(34)+'\n')
cc='/usr/bin/riscv64-unknown-elf-gcc';prefix='/usr/bin/riscv64-unknown-elf-'
flags=['-march=rv32i','-mabi=ilp32','-mno-relax',f'-DREVISION={a.revision}','-DRENDER='+str(int(a.render_test or a.renderer_model))]
if a.render_test or a.renderer_model:flags += ['-DRENDER_DELAY=0','-DLED_MATRIX_0_BASE=0x30000000','-DLED_MATRIX_0_WIDTH=35','-DLED_MATRIX_0_HEIGHT=25']
if a.render_test:flags += ['-DRENDER_TEST=1']
if a.render:raise SystemExit('Use the GUI source builder for peripheral symbols')
sources=[('frontend',DIR/'frontend.S'),('search',DIR/'search.S'),('data',b/'data.s')]
if a.render_test or a.renderer_model:sources.append(('renderer',DIR/'renderer.S'))
objects=[]
for name,src in sources:
    out=b/(name+'.o');subprocess.run([cc,*flags,'-c',str(src),'-o',str(out)],cwd=ROOT,check=True);objects.append(str(out))
elf=b/'solver.elf';subprocess.run([cc,*flags,'-nostdlib','-Wl,--no-relax','-Wl,-T,'+str(DIR/'link.ld'),*objects,'-o',str(elf)],cwd=ROOT,check=True)
size=subprocess.check_output([prefix+'size','-A',str(elf)],text=True);sections={m.group(1):int(m.group(2)) for m in re.finditer(r'^(\.\S+)\s+(\d+)\s+',size,re.M)}
static=sum(sections.get(k,0) for k in ['.data','.bss','.rodata'])
asm=subprocess.check_output([prefix+'objdump','-d',str(elf)],text=True)
if static>131072 or re.search(r'\b(?:mul\w*|div\w*|rem\w*|__(?:mul|div|mod|udiv|umod)\w*)\b',asm):raise SystemExit('ISA/data audit failed')
if subprocess.check_output([prefix+'nm','-u',str(elf)],text=True).strip():raise SystemExit('Unresolved symbols')
manifest={'role':'handwritten RV32I','renderer_test':a.render_test,'renderer_RAM_model':a.renderer_model,'revision':a.revision,'vector':a.vector,'expected_length':a.expect,'sections':sections,'static_bytes':static,'text_bytes':sections['.text'],'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest()}
(b/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(b/'disassembly.txt').write_text(asm)
print(json.dumps(manifest))




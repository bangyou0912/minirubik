#!/usr/bin/env python3
"""Build the final-C GCC -O2 comparison ELF and check its ISA/data budget."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'target/stage4'
P=argparse.ArgumentParser();P.add_argument('--vector',default='21345671111111');P.add_argument('--expect',type=int,default=-1)
a=P.parse_args()
if len(a.vector)!=14 or not a.vector.isascii() or not a.vector.isdigit():raise SystemExit('Expected 14 ASCII input digits')
BUILD=DIR/'build'/a.vector;BUILD.mkdir(parents=True,exist_ok=True)
(BUILD/'data.s').write_text('.section .rodata\n.balign 2\n.globl search_tables\nsearch_tables:\n.incbin "target/stage2/tables.bin"\n.globl input_vector\ninput_vector:\n.asciz "'+a.vector+'"\n.balign 4\n.globl expected_length\nexpected_length:\n.word '+str(a.expect)+'\n')
CC='/usr/bin/riscv64-unknown-elf-gcc';PREFIX='/usr/bin/riscv64-unknown-elf-'
flags=['-O2','-std=c99','-march=rv32i','-mabi=ilp32','-ffreestanding','-fno-builtin','-fno-pic','-mno-relax','-msmall-data-limit=0']
objects=[]
for name,path in [('search',ROOT/'target/stage3/search.c'),('driver',DIR/'reference.c'),('start',DIR/'start.s'),('data',BUILD/'data.s')]:
    out=BUILD/(name+'.o');subprocess.run([CC,*flags,'-c',str(path),'-o',str(out)],cwd=ROOT,check=True);objects.append(str(out))
elf=BUILD/'reference.elf'
subprocess.run([CC,*flags,'-nostdlib','-Wl,--no-relax','-Wl,-T,'+str(DIR/'link.ld'),*objects,'-o',str(elf)],cwd=ROOT,check=True)
sections=subprocess.check_output([PREFIX+'size','-A',str(elf)],text=True)
sizes={m.group(1):int(m.group(2)) for m in re.finditer(r'^(\.\S+)\s+(\d+)\s+',sections,re.M)}
static=sum(sizes.get(n,0) for n in ['.data','.bss','.rodata'])
if static>131072:raise SystemExit(f'Static data over budget: {static}')
asm=subprocess.check_output([PREFIX+'objdump','-d',str(elf)],text=True)
if re.search(r'\b(?:mul\w*|div\w*|rem\w*|__(?:mul|div|mod|udiv|umod)\w*)\b',asm):raise SystemExit('Forbidden arithmetic instruction/helper')
unresolved=subprocess.check_output([PREFIX+'nm','-u',str(elf)],text=True)
if unresolved.strip():raise SystemExit('Unresolved symbols: '+unresolved)
manifest={'role':'GCC final-C reference, not hand-written assembly','vector':a.vector,'expected_length':a.expect,'flags':flags,'sections':sizes,'static_bytes':static,'text_bytes':sizes.get('.text',0),'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest()}
(BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(BUILD/'disassembly.txt').write_text(asm)
print(json.dumps(manifest,indent=2))

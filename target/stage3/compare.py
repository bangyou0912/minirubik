#!/usr/bin/env python3
"""Build C variants, run operation comparison, and audit uninstrumented RV32I C."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'target/stage3'
BUILD=DIR/'build'
BUILD.mkdir(exist_ok=True)
def run(args):
    subprocess.run(args,cwd=ROOT,check=True)
variants=[('base',0,0),('delayed',1,0),('pab',2,0),('pba',2,1),('apb',2,2),('abp',2,3),('bpa',2,4),('bap',2,5)]
objects=[]
for name,variant,order in variants:
    output=BUILD/f'{name}.o'
    run(['gcc','-O3','-std=c99','-Wall','-Wextra','-DS3_COUNT',f'-DS3_VARIANT={variant}',f'-DS3_ORDER={order}',f'-Ds2_solve=solve_{name}',f'-Ds2_position_rank=position_{name}',f'-Ds2_joint_rank=joint_{name}',f'-Ds2_heuristic=heuristic_{name}','-c',str(DIR/'search.c'),'-o',str(output)])
    objects.append(str(output))
run(['gcc','-O3','-std=c99','-Wall','-Wextra',str(DIR/'compare.c'),str(DIR/'reference.c'),str(ROOT/'target/stage2/search.c'),*objects,'-o',str(BUILD/'compare')])
with (DIR/'comparison.txt').open('w') as out:
    subprocess.run([str(BUILD/'compare')],cwd=ROOT,stdout=out,check=True)
print((DIR/'comparison.txt').read_text())

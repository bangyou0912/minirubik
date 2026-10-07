import os
"""Pinned Ripes whole-program measurements for comparable C/assembly builds."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');p.add_argument('--kind',default='asm-r2');p.add_argument('--models',nargs='+',default=['RV32_ISS','RV32_5S']);p.add_argument('--vector');p.add_argument('--expect',type=int,default=-1);a=p.parse_args()
pin=json.loads((ROOT/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']));sha=hashlib.sha256(exe.read_bytes()).hexdigest()
if sha!=pin['sha256']:raise SystemExit('Ripes hash differs from Stage 1 pin')
cases=[(a.vector,a.expect)] if a.vector else [(x['vector'],x['distance']) for x in json.loads((D/'test-cases.json').read_text())['cases']]
out=D/(a.kind+('-'+a.vector if a.vector else '')+('-native' if a.native else '')+'-measurements.json');results={'kind':a.kind,'native_assembly':a.native,'ripes_sha256':sha,'convention':'whole program including parser, printed moves, physical replay, terminating ecall; renderer off','samples':[]}
def number_check(regs,length):
    number=lambda x:int(x,0) if isinstance(x,str) else x
    return number(regs['x12'])==0 and number(regs['x13'])==length+1
for model in a.models:
    for vector,expected in cases:
        b=D/'build'/vector if a.kind=='reference' else D/'build'/a.kind/vector
        elf=b/('reference.elf' if a.kind=='reference' else 'solver.elf')
        if a.native:elf=D/'ripes'/(vector+'.s')
        cmd=[str(exe),'--mode','cli','--src',str(elf),'-t','asm' if a.native else 'elf','--proc',model,'--timeout','180000','--iret','--cycles','--regs','--json']
        started=time.perf_counter();r=subprocess.run(cmd,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode or '{' not in r.stdout:raise SystemExit(f'{model} {vector}: {r.stdout} {r.stderr}')
        index=r.stdout.index('{');data=json.loads(r.stdout[index:]);regs=data['registers']
        num=lambda x:int(x,0) if isinstance(x,str) else x
        length=num(regs['x10']);passed=num(regs['x11'])
        if passed!=1 or (expected>=0 and length!=expected):raise SystemExit(f'Validation failed: {vector} {data}')
        if a.kind.endswith('-render-test'):
            assert number_check(regs, length), (vector,data)
        row={'vector':vector,'model':model,'length':length,'replay_pass':passed,'output':r.stdout[:index].strip(),'wall_s':time.perf_counter()-started,'telemetry':data,'manifest':json.loads((b/'manifest.json').read_text())}
        results['samples'].append(row);out.write_text(json.dumps(results,indent=2)+'\n')
        print(f'{a.kind} {model} {vector}: length={length} PASS iret={data["# instructions retired"]}',flush=True)

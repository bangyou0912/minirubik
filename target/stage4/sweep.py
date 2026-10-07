import os
"""Measure every distance-11 state in pinned Ripes ISS; no sampled worst-case claim."""
from pathlib import Path
import csv,json,hashlib,subprocess,time,concurrent.futures,argparse
from elf_input import Template
D=Path(__file__).resolve().parent;R=D.parents[1]
p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);p.add_argument('--revision',type=int,default=2);p.add_argument('--limit',type=int,default=0);a=p.parse_args()
pin=json.loads((R/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']));sha=hashlib.sha256(exe.read_bytes()).hexdigest()
if sha!=pin['sha256']:raise SystemExit('Wrong pinned Ripes binary')
source=R/'target/stage2/distance11.csv';cases=list(csv.DictReader(source.open()))
if len(cases)!=2644 or len({x['vector'] for x in cases})!=2644 or any(int(x['length'])!=11 for x in cases):raise SystemExit('Bad distance-11 coverage source')
if a.limit:cases=cases[:a.limit]
b=D/'build'/f'asm-r{a.revision}'/'21345671111111';template=Template(b/'solver.elf')
work=D/'build'/'sweep';work.mkdir(exist_ok=True)
started=time.perf_counter();results=[];out=D/f'asm-r{a.revision}-distance11.csv';summary=D/f'asm-r{a.revision}-sweep.json'
def run(case):
    vector=case['vector'];elf=work/(vector+'.elf');content=template.instantiate(vector,11);elf.write_bytes(content)
    command=[str(exe),'--mode','cli','--src',str(elf),'-t','elf','--proc','RV32_ISS','--timeout','180000','--iret','--regs','--json']
    before=time.perf_counter();r=subprocess.run(command,capture_output=True,text=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode or '{' not in r.stdout:raise RuntimeError(f'{vector}: {r.stdout} {r.stderr}')
    at=r.stdout.index('{');j=json.loads(r.stdout[at:]);num=lambda x:int(x,0) if isinstance(x,str) else x
    length=num(j['registers']['x10']);passed=num(j['registers']['x11']);iret=j['# instructions retired']
    if length!=11 or passed!=1 or not 0<iret<=50000000:raise RuntimeError(f'{vector}: length={length} replay={passed} iret={iret}')
    return {'vector':vector,'rank':case['rank'],'length':length,'replay_pass':passed,'iret':iret,'wall_s':time.perf_counter()-before,'elf_sha256':hashlib.sha256(content).hexdigest(),'moves':r.stdout[:at].strip()}
def save(done=False):
    record={'status':'PASS' if done and len(results)==2644 else 'RUNNING' if not done else 'PARTIAL','model':'RV32_ISS','renderer':False,'revision':a.revision,'ripes_sha256':sha,'input_list_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'template_sha256':hashlib.sha256(template.data).hexdigest(),'input_instantiation':'Only input_vector[15] and expected_length[4] are replaced in the linked ELF; code/tables unchanged. This is assembly-time data, no runtime input or oracle.','cases_completed':len(results),'cases_expected':len(cases),'unique_inputs':len({x['vector'] for x in results}),'all_replay_and_length_pass':True,'ceiling':50000000,'maximum':max(results,key=lambda x:x['iret']) if results else None,'minimum_iret':min((x['iret'] for x in results),default=None),'elapsed_wall_s':time.perf_counter()-started,'workers':a.workers,'manifest':json.loads((b/'manifest.json').read_text())}
    summary.write_text(json.dumps(record,indent=2)+'\n')
with out.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['vector','rank','length','replay_pass','iret','wall_s','elf_sha256','moves']);writer.writeheader()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(run,x) for x in cases]
        for future in concurrent.futures.as_completed(futures):
            row=future.result();results.append(row);writer.writerow(row);f.flush()
            if len(results)%50==0:save();print(f'{len(results)}/{len(cases)} max iret={max(x["iret"] for x in results)} elapsed={time.perf_counter()-started:.1f}s',flush=True)
    save(True)
print(f'PASS {len(results)} states, maximum {max(x["iret"] for x in results)}',flush=True)

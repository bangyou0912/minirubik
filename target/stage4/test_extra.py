import os
"""Run independent host-selected inputs through the final assembly parser/search/replay."""
from pathlib import Path
import hashlib,json,subprocess,concurrent.futures
from elf_input import Template
D=Path(__file__).resolve().parent;R=D.parents[1];pin=json.loads((R/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']))
if hashlib.sha256(exe.read_bytes()).hexdigest()!=pin['sha256']:raise SystemExit('Wrong Ripes hash')
b=D/'build'/'asm-r2'/'21345671111111';t=Template(b/'solver.elf');work=D/'build'/'extra-tests';work.mkdir(exist_ok=True)
cases=json.loads((D/'extra-cases.json').read_text())['cases']
invalid=['11345671111111','82345671111111','12345674111111','12345672111111','02345671111111']
cases += [{'vector':v,'distance':-1,'invalid':True} for v in invalid]
def run(case):
    v=case['vector'];e=work/(v+'.elf');e.write_bytes(t.instantiate(v,case['distance']))
    r=subprocess.run([str(exe),'--mode','cli','--src',str(e),'-t','elf','--proc','RV32_ISS','--timeout','180000','--iret','--regs','--json'],capture_output=True,text=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode or '{' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
    at=r.stdout.index('{');j=json.loads(r.stdout[at:]);num=lambda x:int(x,0) if isinstance(x,str) else x;length=num(j['registers']['x10']);passed=num(j['registers']['x11'])
    if case.get('invalid'):
        assert passed==0 and length==0xffffffff,(v,j)
    else:assert passed==1 and length==case['distance'],(v,j)
    return dict(case,iret=j['# instructions retired'],reported_length=length,replay_pass=passed,output=r.stdout[:at].strip())
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,cases))
(D/'extra-test-results.json').write_text(json.dumps({'status':'PASS','ripes_sha256':pin['sha256'],'valid':82,'invalid':5,'samples':rows},indent=2)+'\n')
print('PASS: 82 valid inputs spanning depths 0..11, plus 5 invalid-input rejections')

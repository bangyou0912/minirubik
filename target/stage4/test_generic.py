import os
"""Check the generic editable Ripes source without an expected-length assertion."""
from pathlib import Path
import hashlib,json,subprocess
D=Path(__file__).resolve().parent;R=D.parents[1];pin=json.loads((R/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']));src=D/'ripes/solver.s'
assert hashlib.sha256(exe.read_bytes()).hexdigest()==pin['sha256']
r=subprocess.run([str(exe),'--mode','cli','--src',str(src),'-t','asm','--proc','RV32_ISS','--timeout','180000','--iret','--regs','--json'],capture_output=True,text=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0 and '{' in r.stdout,(r.stdout,r.stderr)
j=json.loads(r.stdout[r.stdout.index('{'):]);num=lambda x:int(x,0) if isinstance(x,str) else x
assert num(j['registers']['x10'])==11 and num(j['registers']['x11'])==1
record={'status':'PASS','input':'21345671111111','expected_length_constant':-1,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'ripes_sha256':pin['sha256'],'telemetry':j}
(D/'generic-source-test.json').write_text(json.dumps(record,indent=2)+'\n')
print(f'Generic native solver PASS; --iret={j["# instructions retired"]}; expected_length=-1')

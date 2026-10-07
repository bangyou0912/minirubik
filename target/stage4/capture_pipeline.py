import os
"""Capture an actual pinned five-stage trace of the short solver query."""
from pathlib import Path
import subprocess,json,hashlib
D=Path(__file__).resolve().parent;R=D.parents[1];pin=json.loads((R/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']))
assert hashlib.sha256(exe.read_bytes()).hexdigest()==pin['sha256']
elf=D/'build/asm-r2/26471352122222/solver.elf'
r=subprocess.run([str(exe),'--mode','cli','--src',str(elf),'-t','elf','--proc','RV32_5S','--timeout','180000','--pipeline','--cycles','--iret','--json'],capture_output=True,text=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0 and '{' in r.stdout,(r.stdout,r.stderr)
j=json.loads(r.stdout[r.stdout.index('{'):]);(D/'pipeline-trace.json').write_text(json.dumps({'ripes_sha256':pin['sha256'],'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'input':'26471352122222','telemetry':j},indent=2)+'\n')
print('Telemetry keys: '+', '.join(j.keys()))
for k,v in j.items():
    if isinstance(v,(list,dict)):
        print(k,str(v)[:1200])
    elif isinstance(v,str):print(k,v[:200])
    else:print(k,v)


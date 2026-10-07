import os
"""Syntax-check GUI source in native Ripes using named RAM symbols, not real I/O."""
from pathlib import Path
import hashlib,json,subprocess
D=Path(__file__).resolve().parent;R=D.parents[1];pin=json.loads((R/'target/measurements.json').read_text());exe=Path(os.environ.get('RIPES_EXE', pin['exe']));assert hashlib.sha256(exe.read_bytes()).hexdigest()==pin['sha256']
b=D/'build/native-render-model';b.mkdir(parents=True,exist_ok=True);rows=[]
for name,length in [('solved-gui.s',0),('walkthrough-gui.s',3),('solver-gui.s',11)]:
    original=(D/'ripes'/name).read_text();text=original.replace('LED_MATRIX_0_BASE','0x30000000').replace('LED_MATRIX_0_WIDTH','35').replace('LED_MATRIX_0_HEIGHT','25')
    text=text.replace('    call assembly_main','    call assembly_main\n    la t0,render_frames\n    lw a2,0(t0)')
    path=b/name;path.write_text(text)
    r=subprocess.run([str(exe),'--mode','cli','--src',str(path),'-t','asm','--proc','RV32_ISS','--timeout','180000','--iret','--regs','--json'],capture_output=True,text=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and '{' in r.stdout,(r.stdout,r.stderr)
    j=json.loads(r.stdout[r.stdout.index('{'):]);num=lambda x:int(x,0) if isinstance(x,str) else x
    assert num(j['registers']['x10'])==length and num(j['registers']['x11'])==1 and num(j['registers']['x12'])==length+1,(name,j)
    rows.append({'GUI_source':name,'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'RAM_test_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'length':length,'frames':length+1,'telemetry':j})
    print(f'{name}: native assembler PASS, length={length}, frames={length+1}',flush=True)
(D/'native-renderer-tests.json').write_text(json.dumps({'status':'PASS','device':'RAM stand-in; actual GUI peripheral not tested','ripes_sha256':pin['sha256'],'samples':rows},indent=2)+'\n')

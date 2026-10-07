"""Reproduce sparse-memory slope and simulator throughput; never run baseline."""
import ctypes, ctypes.wintypes as wt, hashlib, json, pathlib, statistics, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parent
EXE = pathlib.Path.home() / 'Apps/Ripes-continuous/Ripes.exe'
class Counters(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('faults', wt.DWORD)] + [(n, ctypes.c_size_t) for n in ('peak_ws','ws','peak_paged','paged','peak_nonpaged','nonpaged','commit','peak_commit')]
def run(n, model):
    command = [str(EXE), '--mode', 'cli', '--src', str(ROOT/'memory_probe.s'), '-t', 'asm', '--proc', model, '--timeout', '60000', '--reginit', f'gpr:10={n}', '--iret', '--cycles', '--exectime', '--json']
    start=time.perf_counter()
    p=subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    out,err=p.communicate()
    wall=time.perf_counter()-start
    c=Counters(); c.cb=ctypes.sizeof(c)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(wt.HANDLE(int(p._handle)), ctypes.byref(c), c.cb): raise ctypes.WinError()
    if p.returncode: raise RuntimeError((command,out,err))
    data=json.loads(out[out.index('{'):])
    return dict(guest_bytes=n,model=model,peak_ws=c.peak_ws,peak_commit=c.peak_commit,wall_s=wall,telemetry=data)
results=dict(exe=str(EXE),sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),samples=[])
for n,model in [(0,'RV32_ISS'),(4096,'RV32_ISS'),(1048576,'RV32_ISS'),(65536,'RV32_5S')]:
    for repeat in range(3):
        row=run(n,model); results['samples'].append(row)
        print(json.dumps(row),flush=True)
        (ROOT/'measurements.json').write_text(json.dumps(results,indent=2))

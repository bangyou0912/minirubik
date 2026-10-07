"""Extract first real edge and commit timings from the Ripes stage trace."""
from pathlib import Path
import json,csv,io
D=Path(__file__).resolve().parent
j=json.loads((D/'pipeline-trace.json').read_text());raw=j['telemetry']['pipeline'];rows=list(csv.reader(io.StringIO(raw),delimiter='\t'));cycles=rows[0][1:]
entries=[{'instruction':r[0],'first':[{ 'cycle':int(cycles[i]),'stage':v} for i,v in enumerate(r[1:]) if v][:12]} for r in rows[1:] if r]
patterns=['lbu x28 0 x5','addi x28 x28 -49','bgeu x28 x31','sb x28 0 x30','slli x29 x5 1','add x29 x21 x29','lhu x5 0 x29','lhu x6 0 x29','lhu x7 0 x29','lbu x30 0 x29','bltu x31 x30','sb x29 192 x30','sh x5 6 x18','sh x6 8 x18','sh x7 10 x18']
selected=[e for e in entries if e['first'] and any(e['instruction'].startswith(p) for p in patterns)]
record={'input':j['input'],'model':'RV32_5S','iret':j['telemetry']['# instructions retired'],'cycles':j['telemetry']['cycles'],'source':'Observed stage occupancy from --pipeline; no GUI wire values captured','capture_window_cycles':[min(int(c) for c in cycles if c.isdigit()),max(int(c) for c in cycles if c.isdigit())],'events':selected}
(D/'pipeline-events.json').write_text(json.dumps(record,indent=2)+'\n')
for e in selected:print(e['instruction']+': '+', '.join(str(v['cycle'])+' '+v['stage'] for v in e['first'][:7]))

#!/usr/bin/env python3
"""Summarize logical operation counts and audit compiler output; no Ripes claims."""
from pathlib import Path
import csv, json, re, subprocess
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'target/stage3'
BUILD=DIR/'build'
BUILD.mkdir(exist_ok=True)
rows=list(csv.DictReader((DIR/'operations.csv').open()))
totals={r['variant']:r for r in rows if r['vector']=='TOTAL_2644'}
metrics=['edges','transition_reads','frame_initializations','path_writes','max_comparisons','threshold_comparisons','pruned']
def counts(r):
    out={k:int(r[k]) for k in metrics}
    out['pdb_reads']=sum(int(r[k]) for k in ['pdb_P','pdb_A','pdb_B'])
    return out
baseline=counts(totals['baseline']);selected=counts(totals['ABP'])
result={'scope':'2644 distance-11 states, all IDA* bounds; host logical operations, not retired instructions',
        'selected':'ABP: joint A, joint B, permutation',
        'baseline':baseline,'selected_counts':selected,
        'reductions_percent':{k:100*(baseline[k]-selected[k])/baseline[k] for k in ['pdb_reads','frame_initializations','path_writes']},
        'cases':{v:{name:counts(next(r for r in rows if r['vector']==v and r['variant']==name)) for name in ['baseline','delayed','ABP']} for v in ['21345671111111','54721631111111']},
        'target_data_bytes':80844,'target_instruction_budget_status':'pending Stage 4 measurements'}
compiler='/usr/bin/riscv64-unknown-elf-gcc'
result['compiler']=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
for name,source in [('selected',DIR/'search.c'),('stage2',ROOT/'target/stage2/search.c')]:
    asm=BUILD/f'rv32i-{name}.s'
    subprocess.run([compiler,'-O2','-std=c99','-march=rv32i','-mabi=ilp32','-ffreestanding','-S',str(source),'-o',str(asm)],check=True,cwd=ROOT)
    text=asm.read_text()
    forbidden=re.findall(r'^\s*(?:mul\w*|div\w*|rem\w*)\s+.*$',text,re.M)
    helpers=re.findall(r'\b__(?:mul|div|mod|udiv|umod)\w*',text)
    if forbidden or helpers:raise SystemExit(f'Unexpected multiply/divide requirement in {name}: {forbidden} {helpers}')
    if name=='selected':
        preprocessed=subprocess.check_output([compiler,'-march=rv32i','-mabi=ilp32','-ffreestanding','-E','-P',str(source)],text=True,cwd=ROOT)
        if re.search(r'stats\s*->',preprocessed):raise SystemExit('Diagnostic counter access remains in production preprocessing')
result['rv32i_audit']={'multiply_divide_opcodes':0,'multiply_divide_helpers':0,'production_counter_accesses':0,
    'row_pointer_result':'Compiler still synthesizes non-power-of-two face strides with shifts/adds; no addressing-speed claim.'}
result['verification']={
    'all_state_search_passed': 'PASS: all 3674160 states' in (DIR/'all-state-verification.txt').read_text(),
    'all_state_log':'target/stage3/all-state-verification.txt',
    'sanitizers_passed': 'PASS: ASan+UBSan' in (DIR/'sanitizer-verification.txt').read_text(),
    'sanitizer_log':'target/stage3/sanitizer-verification.txt',
    'path_and_edge_equivalence':'Eight counted variants match original Stage 2 for all 2644 distance-11 states and solved state.'}
wall_file=DIR/'wall-time.txt'
if wall_file.exists():
    wall_values=dict(line.split() for line in wall_file.read_text().splitlines() if line.strip())
    result['verification'].update({
        'H3_wall_seconds':float(wall_values['real']),
        'H3_user_seconds':float(wall_values['user']),
        'H3_system_seconds':float(wall_values['sys'])})
result['verification']['H4']='Not applicable: byte PDBs and uint16 transitions; no packed accessor in production.'
(DIR/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))




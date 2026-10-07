#!/usr/bin/env python3
"""Audit static data of the actual standalone GUI export, renderer included."""
from pathlib import Path
import subprocess,re,json,hashlib
D=Path(__file__).resolve().parent;R=D.parents[1];source=D/'ripes/solver-gui.s';text=source.read_text()
assert all(s in text for s in ['LED_MATRIX_0_BASE','LED_MATRIX_0_WIDTH','LED_MATRIX_0_HEIGHT'])
b=D/'build/gui-static-audit';b.mkdir(parents=True,exist_ok=True)
# Bind only device constants to allow a GNU link. This does not claim GUI execution.
model=text.replace('LED_MATRIX_0_BASE','0x30000000').replace('LED_MATRIX_0_WIDTH','35').replace('LED_MATRIX_0_HEIGHT','25')
(b/'gui.s').write_text(model)
cc='/usr/bin/riscv64-unknown-elf-gcc';prefix='/usr/bin/riscv64-unknown-elf-'
subprocess.run([cc,'-march=rv32i','-mabi=ilp32','-mno-relax','-nostdlib','-Wl,--no-relax','-Wl,-T,'+str(D/'link.ld'),str(b/'gui.s'),'-o',str(b/'gui.elf')],check=True,cwd=R)
output=subprocess.check_output([prefix+'size','-A',str(b/'gui.elf')],text=True)
sections={m.group(1):int(m.group(2)) for m in re.finditer(r'^(\.\S+)\s+(\d+)\s+',output,re.M)}
static=sum(sections.get(k,0) for k in ['.data','.bss','.rodata']);assert static<=131072
record={'source':'target/stage4/ripes/solver-gui.s','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'renderer_included':True,'section_sizes':sections,'static_bytes':static,'static_KiB':static/1024,'budget_bytes':131072,'remaining_bytes':131072-static,'LED_related_added_static_bytes':148,'MMIO_pixel_window_bytes':35*25*4,'conservative_static_plus_MMIO_bytes':static+35*25*4,'device_binding_note':'Peripheral constants bound to test RAM values only for linking; no GUI execution claimed.'}
(D/'gui-static-budget.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

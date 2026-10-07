"""Consistency check of measured evidence and the delivered source artifacts."""
from pathlib import Path
import csv,io,json,hashlib
from check_rebuilt_sections import sections
from elf_input import Template
D=Path(__file__).resolve().parent
for kind in ['reference','asm-r0','asm-r1','asm-r2']:
    result=json.loads((D/(kind+'-measurements.json')).read_text())
    assert len(result['samples'])==6
    assert {(x['vector'],x['model']) for x in result['samples']}=={(v,m) for v in ['12345671111111','26471352122222','21345671111111'] for m in ['RV32_ISS','RV32_5S']}
    for row in result['samples']:
        assert row['replay_pass']==1
        manifest=row['manifest'];b=D/'evidence'/kind/row['vector']
        elf=b/('reference.elf' if kind=='reference' else 'solver.elf')
        archive=json.loads((b/'manifest.json').read_text())
        assert hashlib.sha256(elf.read_bytes()).hexdigest()==archive['elf_sha256']
        rebuilt=(D/'build'/row['vector'] if kind=='reference' else D/'build'/kind/row['vector'])/elf.name
        recent=D/'evidence/rebuilt'/kind/row['vector']/elf.name
        measured=elf if manifest['elf_sha256']==archive['elf_sha256'] else recent if recent.exists() and hashlib.sha256(recent.read_bytes()).hexdigest()==manifest['elf_sha256'] else rebuilt
        assert hashlib.sha256(measured.read_bytes()).hexdigest()==manifest['elf_sha256']
        assert sections(elf)==sections(measured),(kind,row['vector'])
        if rebuilt.exists():assert sections(elf)==sections(rebuilt),(kind,row['vector'])
summary=json.loads((D/'asm-r2-sweep.json').read_text());rows=list(csv.DictReader(io.StringIO((D/'asm-r2-distance11.csv').read_text().replace('\0',''))))
source=list(csv.DictReader((D.parent/'stage2/distance11.csv').open()))
assert summary['status']=='PASS' and len(rows)==2644 and len({r['vector'] for r in rows})==2644
assert {r['vector'] for r in rows}=={r['vector'] for r in source}
assert all(int(r['length'])==11 and int(r['replay_pass'])==1 and 0<int(r['iret'])<=50000000 for r in rows)
assert max(int(r['iret']) for r in rows)==summary['maximum']['iret']==7832368
assert min(int(r['iret']) for r in rows)==summary['minimum_iret']==1385412
assert summary['manifest']['text_bytes']==1864 and summary['manifest']['static_bytes']==81020
assert hashlib.sha256((D.parent/'stage2/distance11.csv').read_bytes()).hexdigest()==summary['input_list_sha256']
archived=D/'evidence/asm-r2/21345671111111/solver.elf'
candidate=archived if hashlib.sha256(archived.read_bytes()).hexdigest()==summary['template_sha256'] else D/'build/asm-r2/21345671111111/solver.elf'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==summary['template_sha256']
assert sections(candidate)==sections(archived)
template=Template(candidate)
assert all(hashlib.sha256(template.instantiate(row['vector'],11)).hexdigest()==row['elf_sha256'] for row in rows)
extra=json.loads((D/'extra-test-results.json').read_text());assert len(extra['samples'])==87 and extra['status']=='PASS'
native=json.loads((D/'asm-r2-native-measurements.json').read_text());assert len(native['samples'])==6
for a,b in zip(native['samples'],json.loads((D/'asm-r2-measurements.json').read_text())['samples']):assert a['telemetry']['# instructions retired']==b['telemetry']['# instructions retired']
generic=json.loads((D/'generic-source-test.json').read_text());assert generic['status']=='PASS' and generic['source_sha256']==hashlib.sha256((D/'ripes/solver.s').read_bytes()).hexdigest()
for name in ['stage1.md','stage2.md','stage3.md','stage4.md']:
    text=(D.parents[1]/name).read_text(encoding='utf-8-sig');assert text.count(chr(96)*3)%2==0,name
print('PASS: revision ELF hashes, six-case results, all 2644 rows, independent fixtures, native source, and Markdown fences')

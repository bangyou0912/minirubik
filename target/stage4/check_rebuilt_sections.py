"""Compare execution-relevant ELF sections; paths in symbol tables may differ."""
from pathlib import Path
import hashlib, json, struct
D = Path(__file__).resolve().parent

def sections(path):
    data = path.read_bytes()
    assert data[:7] == b'\x7fELF\x01\x01\x01'
    offset = struct.unpack_from('<I', data, 32)[0]
    stride, count, names_index = struct.unpack_from('<HHH', data, 46)
    headers = [struct.unpack_from('<10I', data, offset + i * stride) for i in range(count)]
    strings = headers[names_index]
    names = data[strings[4]:strings[4] + strings[5]]
    result = {}
    for h in headers:
        if not h[2] & 2:  # Only allocated program/data sections, not ELF metadata.
            continue
        name = names[h[0]:names.index(b'\0', h[0])].decode()
        payload = bytes(h[5]) if h[1] == 8 else data[h[4]:h[4] + h[5]]
        result[name] = {'address': h[3], 'bytes': h[5], 'sha256': hashlib.sha256(payload).hexdigest()}
    return result

def main():
    rows = []
    for kind in ['reference', 'asm-r0', 'asm-r1', 'asm-r2']:
        for vector in ['12345671111111', '26471352122222', '21345671111111']:
            filename = 'reference.elf' if kind == 'reference' else 'solver.elf'
            historical = D / 'evidence' / kind / vector / filename
            rebuilt = (D / 'build' / vector if kind == 'reference' else D / 'build' / kind / vector) / filename
            assert rebuilt.exists(), f'Rebuild first: {rebuilt}'
            before, after = sections(historical), sections(rebuilt)
            assert before == after, f'Execution sections changed: {kind} {vector}'
            rows.append({'kind': kind, 'vector': vector, 'sections': after,
                         'whole_elf_sha256': hashlib.sha256(rebuilt.read_bytes()).hexdigest()})
    record = {'status': 'PASS', 'convention': 'All SHF_ALLOC section addresses, sizes and bytes match archived measured ELFs; metadata may differ.', 'samples': rows}
    (D / 'rebuilt-section-verification.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS: all 12 rebuilt ELFs match every execution-relevant archived section')

if __name__ == '__main__':main()

from pathlib import Path
import csv,json,io
D=Path(__file__).resolve().parent
rows=list(csv.DictReader(io.StringIO((D/'asm-r2-distance11.csv').read_text().replace('\0',''))))
assert len(rows)==2644 and len({r['vector'] for r in rows})==2644
rows += [r for r in json.loads((D/'extra-test-results.json').read_text())['samples'] if not r.get('invalid')]
lines=[]
for row in rows:
    text=row.get('moves',row.get('output','')).replace('\0','').split('Program exited with code:')[0].strip()
    tokens=text.split();assert all(t in ['R','R2',"R'",'B','B2',"B'",'D','D2',"D'"] for t in tokens)
    length=int(row.get('length',row.get('distance')));assert len(tokens)==length
    lines.append(row['vector']+' '+str(length)+' '+' '.join(tokens))
(D/'build/printed-paths.txt').write_text('\n'.join(lines)+'\n')
print(f'Prepared {len(lines)} recorded paths for independent host verification')

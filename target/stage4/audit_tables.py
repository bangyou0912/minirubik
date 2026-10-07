"""H2 table population/range/maximum/goal audit of the actual linked bytes."""
from pathlib import Path
import json, struct, hashlib
D=Path(__file__).resolve().parent
data=(D.parent/'stage2/tables.bin').read_bytes()
assert len(data)==80640
record={'tables_sha256':hashlib.sha256(data).hexdigest(),'static_table_bytes':len(data)}
offset=0
for name,n,goals in [('permutation_transition',5040,[0]),('joint_transition',5670,[0,2916])]:
    values=struct.unpack_from('<'+'H'*(3*n),data,offset)
    assert all(0<=v<n for v in values)
    record[name]={'entries':len(values),'expected_entries':3*n,'min':min(values),'max':max(values),'goal_indices':goals,'goal_quarter_turn_values':[[values[f*n+g] for f in range(3)] for g in goals]}
    offset+=6*n
for name,n,goal in [('permutation_PDB',5040,0),('joint_A_PDB',5670,0),('joint_B_PDB',5670,2916)]:
    values=data[offset:offset+n]
    assert len(values)==n and 255 not in values and max(values)==7
    assert values[goal]==0 and values.count(0)==1
    record[name]={'populated':n,'expected_entries':n,'max':max(values),'goal_index':goal,'goal_distance':values[goal],'unique_zero':True}
    offset+=n
assert offset==len(data)
record['H4']='Not applicable: byte distances and uint16 transitions; no packed accessor.'
(D/'table-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: all 80640 table bytes, full PDB coverage, maximum 7 and solved distances 0')
